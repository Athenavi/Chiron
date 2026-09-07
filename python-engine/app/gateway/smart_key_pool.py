"""
智能 API Key 池 — 多 Key 轮询 + 动态权重 + 熔断
管理端添加的 Key 使用 APP_SECRET 派生的 AES-256-GCM 密钥加密后存入
admin_api_keys 表（provider + encrypted_key 行），不再明文落盘 JSON。
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

# 加密密钥派生域：与 Go 侧 internal/settings 的 AES-256-GCM 风格一致，
# 但使用独立 domain 隔离，密文互不通用。主密钥 = APP_SECRET。
_ENC_DOMAIN = "chiron-admin-api-key:"
# 密文格式前缀：`v1:` + base64(nonce || ciphertext)（与 Go settings 层一致，便于识别与互操作）
_CIPHER_PREFIX = "v1:"
_NONCE_LEN = 12


class ApiKeyDBUnavailable(RuntimeError):
    """PostgreSQL 不可用/未初始化。管理端密钥持久化硬依赖数据库。"""


def _encryption_key(app_secret: str) -> bytes:
    if not app_secret:
        raise ApiKeyDBUnavailable(
            "APP_SECRET not configured; cannot derive admin api key encryption key"
        )
    return hashlib.sha256((_ENC_DOMAIN + app_secret).encode("utf-8")).digest()


def encrypt_key(plain: str, app_secret: str) -> str:
    """AES-256-GCM 加密：v1:base64(nonce || ciphertext)。nonce 每次随机。"""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = uuid.uuid4().bytes  # 128-bit -> 截断为 12 字节
    nonce = nonce[:_NONCE_LEN]
    ct = AESGCM(_encryption_key(app_secret)).encrypt(nonce, plain.encode("utf-8"), None)
    return _CIPHER_PREFIX + base64.b64encode(nonce + ct).decode("ascii")


def decrypt_key(cipher: str, app_secret: str) -> str:
    """解密 encrypt_key 产生的密文。"""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if not cipher.startswith(_CIPHER_PREFIX):
        raise ValueError("invalid admin api key ciphertext")
    raw = base64.b64decode(cipher[len(_CIPHER_PREFIX):])
    if len(raw) < _NONCE_LEN:
        raise ValueError("invalid admin api key ciphertext length")
    nonce, ct = raw[:_NONCE_LEN], raw[_NONCE_LEN:]
    return AESGCM(_encryption_key(app_secret)).decrypt(nonce, ct, None).decode("utf-8")


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _key_id_digest(key_id: str) -> str:
    """从 key_id（provider-<sha256[:12]>）解析出 12 位哈希前缀；非法格式返回空串。"""
    if "-" not in key_id:
        return ""
    digest = key_id.rsplit("-", 1)[1]
    if len(digest) == 12 and all(c in "0123456789abcdef" for c in digest):
        return digest
    return ""


def provider_key_hash(provider: str, key: str) -> str:
    """provider+key 的完整 sha256 hex：写入 admin_api_keys.key_hash（唯一约束，防重复）。"""
    return hashlib.sha256(f"{provider}:{key}".encode("utf-8")).hexdigest()


class KeyStatus(str, Enum):
    """Key 状态"""

    ACTIVE = "active"  # 正常
    RATE_LIMITED = "rate_limited"  # 限流中
    CIRCUIT_OPEN = "circuit_open"  # 熔断


@dataclass
class CircuitBreaker:
    """熔断器"""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _state: str = field(default="closed", init=False)

    def record_success(self):
        """记录成功"""
        self._failure_count = 0
        self._state = "closed"

    def record_failure(self):
        """记录失败"""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            logger.warning(
                "Circuit breaker opened after %d failures", self._failure_count
            )

    def is_open(self) -> bool:
        """检查是否熔断"""
        if self._state == "closed":
            return False

        # 检查是否可以恢复
        if time.time() - self._last_failure_time > self.recovery_timeout:
            self._state = "half_open"
            return False

        return True

    def is_half_open(self) -> bool:
        """检查是否半开"""
        return self._state == "half_open"


@dataclass
class APIKeyInfo:
    """API Key 信息"""

    key: str
    provider: str
    weight: float = 1.0
    failures: int = 0
    last_used: float = 0.0
    status: KeyStatus = KeyStatus.ACTIVE
    circuit_breaker: Optional[CircuitBreaker] = None
    remark: str = ""


class SmartAPIKeyPool:
    """
    智能 API Key 池

    功能：
    1. 多 Key 轮询，绕过单账户 Rate Limit
    2. 动态权重，根据延迟和成功率调整
    3. 熔断机制，Key 失效时自动切换
    """

    def __init__(
        self,
        keys: dict[str, list[str]] | None = None,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        weight_decay: float = 0.5,
        weight_recovery: float = 1.1,
        max_weight: float = 2.0,
        app_secret: str | None = None,
        db=None,
    ):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._weight_decay = weight_decay
        self._weight_recovery = weight_recovery
        self._max_weight = max_weight
        self._lock = asyncio.Lock()

        # 加密主密钥：管理端密钥加密落库依赖 APP_SECRET（与 Go 端 settings 加密同源但独立 domain）。
        # 未显式传入时延迟从引擎 settings 读取（保持单测可用构造）。
        self._app_secret = app_secret
        # DB pool：默认 None → 延迟取引擎全局 pool（app.db.get_pool）；测试可注入 fake。
        self._db = db

        # 初始化 Key 池
        self._pools: dict[str, list[APIKeyInfo]] = {}
        if keys:
            for provider, key_list in keys.items():
                self._pools[provider] = [
                    APIKeyInfo(
                        key=key,
                        provider=provider,
                        circuit_breaker=CircuitBreaker(
                            failure_threshold=failure_threshold,
                            recovery_timeout=recovery_timeout,
                        ),
                    )
                    for key in key_list
                ]

    def _secret(self) -> str:
        """返回加密主密钥（APP_SECRET）。延迟加载并缓存，避免循环 import。"""
        if self._app_secret is None:
            from app.config import settings

            self._app_secret = settings.app_secret or ""
        return self._app_secret

    async def get_key(self, provider: str) -> Optional[str]:
        """
        获取可用的 API Key

        Args:
            provider: 提供商名称

        Returns:
            API Key，无可用则返回 None
        """
        # 锁外获取 pool 快照（只读操作）
        pool = self._pools.get(provider, [])
        if not pool:
            return None

        # 锁外过滤可用 Key（只读操作）
        available = [
            k
            for k in pool
            if not k.circuit_breaker or not k.circuit_breaker.is_open()
        ]

        if not available:
            # 全部熔断，计算最短等待时间
            logger.warning(
                "All keys for %s are circuit open, waiting for recovery", provider
            )
            wait_time = self._calc_recovery_wait(pool)
            if wait_time < float("inf"):
                # 释放锁后等待，避免死锁
                pass
            else:
                return None
        else:
            # 按权重选择（锁内保护 last_used 写入）
            total_weight = sum(k.weight for k in available)
            r = random.uniform(0, total_weight)

            cumulative = 0
            for key_info in available:
                cumulative += key_info.weight
                if r <= cumulative:
                    key_info.last_used = time.time()
                    return key_info.key

            # Fallback: 返回第一个
            available[0].last_used = time.time()
            return available[0].key

        # 在锁外等待恢复，然后重试
        logger.info("Waiting %.1f seconds for key recovery", wait_time)
        await asyncio.sleep(wait_time)
        return await self.get_key(provider)

    def _calc_recovery_wait(self, pool: list) -> float:
        """计算最近的 Key 恢复等待时间（需在锁内调用）"""
        min_wait = float("inf")
        for k in pool:
            if k.circuit_breaker and k.circuit_breaker.is_open():
                wait_time = k.circuit_breaker.recovery_timeout - (
                    time.time() - k.circuit_breaker._last_failure_time
                )
                min_wait = min(min_wait, max(0, wait_time))
        return min_wait

    async def report_success(self, key: str, latency: float = 0.0) -> None:
        """
        报告成功，调整权重

        Args:
            key: API Key
            latency: 延迟（毫秒）
        """
        async with self._lock:
            for pool in self._pools.values():
                for k in pool:
                    if k.key == key:
                        k.failures = max(0, k.failures - 1)
                        k.weight = min(
                            self._max_weight, k.weight * self._weight_recovery
                        )
                        k.status = KeyStatus.ACTIVE

                        if k.circuit_breaker:
                            k.circuit_breaker.record_success()

                        return

    async def report_failure(self, key: str, error: str = "") -> None:
        """
        报告失败，降低权重或熔断

        Args:
            key: API Key
            error: 错误信息
        """
        async with self._lock:
            for pool in self._pools.values():
                for k in pool:
                    if k.key == key:
                        k.failures += 1
                        k.weight *= self._weight_decay

                        if k.circuit_breaker:
                            k.circuit_breaker.record_failure()

                            if k.circuit_breaker.is_open():
                                k.status = KeyStatus.CIRCUIT_OPEN
                                logger.warning(
                                    "Key %s circuit opened: %s", key[:20], error
                                )

                        return

    def _db_pool(self):
        """返回数据库 pool；未初始化/不可用抛 ApiKeyDBUnavailable。"""
        if self._db is not None:
            return self._db
        try:
            from app.db import get_pool

            return get_pool()
        except Exception as exc:
            raise ApiKeyDBUnavailable(
                "PostgreSQL unavailable: admin api key persistence requires database"
            ) from exc

    async def load_from_db(self) -> int:
        """启动时把 admin_api_keys 中加密的管理端密钥解密载入内存（幂等，与 env 注入去重）。

        Returns:
            成功载入条数。DB 不可用时抛 ApiKeyDBUnavailable（由调用方决定告警/继续）。
        """
        secret = self._secret()
        pool = self._db_pool()
        rows = await pool.fetch(
            """
            SELECT provider, encrypted_key, description, status
            FROM admin_api_keys
            WHERE provider IS NOT NULL AND provider <> ''
              AND encrypted_key IS NOT NULL AND encrypted_key <> ''
            """
        )
        loaded = 0
        async with self._lock:
            for row in rows:
                provider = str(row["provider"]).strip()
                cipher = str(row["encrypted_key"]).strip()
                if not provider or not cipher:
                    continue
                try:
                    key = decrypt_key(cipher, secret)
                except Exception:
                    logger.exception(
                        "skip admin api key row: decrypt failed for provider=%s", provider
                    )
                    continue
                pool_by_provider = self._pools.setdefault(provider, [])
                if any(k.key == key for k in pool_by_provider):
                    continue  # 与 env 注入的重复项去重
                try:
                    status = KeyStatus(str(row["status"] or "active"))
                except ValueError:
                    status = KeyStatus.ACTIVE
                pool_by_provider.append(
                    APIKeyInfo(
                        key=key,
                        provider=provider,
                        remark=str(row["description"] or ""),
                        status=status,
                        circuit_breaker=CircuitBreaker(
                            failure_threshold=self._failure_threshold,
                            recovery_timeout=self._recovery_timeout,
                        ),
                    )
                )
                loaded += 1
        logger.info("loaded %d admin api key(s) from admin_api_keys table", loaded)
        return loaded

    async def _persist_row_locked(self, provider: str, key: str, remark: str, status: str) -> None:
        """把密钥加密写入 admin_api_keys（须在 _lock 内调用；DB 不可用抛错，不落明文）。"""
        secret = self._secret()
        pool = self._db_pool()
        encrypted = encrypt_key(key, secret)
        key_hash = provider_key_hash(provider, key)
        await pool.execute(
            """
            INSERT INTO admin_api_keys
                (id, key_hash, name, status, created_at, updated_at, description, provider, encrypted_key)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (key_hash) DO UPDATE SET
                provider = EXCLUDED.provider,
                encrypted_key = EXCLUDED.encrypted_key,
                description = EXCLUDED.description,
                status = EXCLUDED.status,
                updated_at = EXCLUDED.updated_at
            """,
            str(uuid.uuid4()),
            key_hash,
            provider,  # name 列冗余存 provider，便于人工核对行归属
            status,
            _now_iso(),
            _now_iso(),
            remark or None,
            provider,
            encrypted,
        )

    async def add_key(
        self, provider: str, key: str, remark: str = "", persist: bool = True
    ) -> None:
        """添加 Key。

        persist=True（管理端）：先加密写入 admin_api_keys（DB 不可用抛 ApiKeyDBUnavailable，
        不落明文），成功后才入内存；重复 key 仅刷新备注。
        persist=False（env 注入）：仅内存，重启由 env 重新注入。
        """
        async with self._lock:
            pool = self._pools.setdefault(provider, [])
            for existing in pool:
                if existing.key == key:
                    if remark and remark != existing.remark:
                        existing.remark = remark
                        if persist:
                            await self._persist_row_locked(
                                provider, key, remark, existing.status.value
                            )
                    return

            if persist:
                await self._persist_row_locked(provider, key, remark, KeyStatus.ACTIVE.value)

            pool.append(
                APIKeyInfo(
                    key=key,
                    provider=provider,
                    remark=remark,
                    circuit_breaker=CircuitBreaker(
                        failure_threshold=self._failure_threshold,
                        recovery_timeout=self._recovery_timeout,
                    ),
                )
            )

    async def remove_key(self, provider: str, key: str) -> bool:
        """删除 Key（DB 行按 key_hash 删除；DB 不可用抛错）"""
        pool = self._db_pool()
        digest = provider_key_hash(provider, key)
        await pool.execute(
            "DELETE FROM admin_api_keys WHERE provider = $1 AND key_hash = $2",
            provider,
            digest,
        )
        async with self._lock:
            bucket = self._pools.get(provider, [])
            for i, k in enumerate(bucket):
                if k.key == key:
                    bucket.pop(i)
                    if not bucket:
                        del self._pools[provider]
                    return True
        return False

    @staticmethod
    def key_id(provider: str, key: str) -> str:
        """稳定 ID：provider + key 指纹（不泄露完整 key，可用于管理端按 ID 定位）"""
        digest = hashlib.sha256(f"{provider}:{key}".encode()).hexdigest()[:12]
        return f"{provider}-{digest}"

    async def update_key_status(self, key_id: str, status: str) -> bool:
        """
        按 ID 更新 Key 状态（active / rate_limited / circuit_open）
        ID 为 key_id（provider + sha256[:12]），DB 行按 key_hash 前缀定位同步更新。

        Returns:
            是否找到并更新（非法状态值或 ID 不存在返回 False；DB 不可用抛错）
        """
        try:
            new_status = KeyStatus(status)
        except ValueError:
            return False

        # 同步 DB 中的状态（管理端密钥行；env 密钥无行，affected=0 仅更新内存）
        pool = self._db_pool()
        digest = _key_id_digest(key_id)
        if digest:
            await pool.execute(
                "UPDATE admin_api_keys SET status = $1, updated_at = $2 WHERE left(key_hash, 12) = $3",
                new_status.value,
                _now_iso(),
                digest,
            )

        async with self._lock:
            for bucket in self._pools.values():
                for k in bucket:
                    if self.key_id(k.provider, k.key) == key_id:
                        k.status = new_status
                        # 手动恢复为 active 时重置熔断器，否则下次 get_key 仍被熔断拦截
                        if new_status == KeyStatus.ACTIVE and k.circuit_breaker:
                            k.circuit_breaker.record_success()
                        return True
        return False

    async def remove_key_by_id(self, key_id: str) -> bool:
        """按 ID 删除 Key（管理端路径删除，无需请求体携带完整 key）。
        DB 行按 key_hash 前缀定位删除；env 密钥无 DB 行，仅移除内存。"""
        pool = self._db_pool()
        digest = _key_id_digest(key_id)
        if digest:
            await pool.execute(
                "DELETE FROM admin_api_keys WHERE left(key_hash, 12) = $1",
                digest,
            )
        async with self._lock:
            for provider, bucket in self._pools.items():
                for i, k in enumerate(bucket):
                    if self.key_id(k.provider, k.key) == key_id:
                        bucket.pop(i)
                        if not bucket:
                            del self._pools[provider]
                        return True
        return False

    def get_stats(self) -> dict:
        """获取统计信息"""
        stats = {
            "total": 0,
            "active": 0,
            "rate_limited": 0,
            "circuit_open": 0,
            "providers": {},
        }

        for provider, pool in self._pools.items():
            provider_stats = {
                "total": len(pool),
                "active": 0,
                "rate_limited": 0,
                "circuit_open": 0,
            }

            for k in pool:
                stats["total"] += 1

                if k.status == KeyStatus.ACTIVE:
                    stats["active"] += 1
                    provider_stats["active"] += 1
                elif k.status == KeyStatus.RATE_LIMITED:
                    stats["rate_limited"] += 1
                    provider_stats["rate_limited"] += 1
                elif k.status == KeyStatus.CIRCUIT_OPEN:
                    stats["circuit_open"] += 1
                    provider_stats["circuit_open"] += 1

            stats["providers"][provider] = provider_stats

        return stats

    def get_all_keys(self) -> list[dict]:
        """获取所有 Key 信息（含稳定 id，供管理端更新/删除定位）"""
        keys = []
        for provider, pool in self._pools.items():
            for k in pool:
                keys.append(
                    {
                        "id": self.key_id(k.provider, k.key),
                        "provider": k.provider,
                        "key": k.key[:20] + "...",
                        "weight": k.weight,
                        "failures": k.failures,
                        "status": k.status.value,
                        "last_used": k.last_used,
                        "remark": k.remark,
                    }
                )
        return keys
