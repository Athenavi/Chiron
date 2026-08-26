"""
Alembic env configuration.
Resolves the database URL from:
  1. DATABASE_DSN environment variable
  2. install.lock (AES-256-GCM decrypted with APP_SECRET)
  3. alembic.ini fallback
"""
import base64
import hashlib
import hmac
import json
import os
from logging.config import fileConfig
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from dotenv import load_dotenv

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 加载 .env 文件 - 支持多个位置
project_root = Path(__file__).parent.parent

# 按优先级尝试加载 .env 文件
env_candidates = [
    project_root / '.env',              # 根目录 .env
    project_root / 'config' / '.env',   # config 目录 .env（安装向导写入位置）
]
env_loaded = False
for env_file in env_candidates:
    if env_file.exists():
        load_dotenv(env_file, override=True)
        print(f"[Alembic] Loaded .env from {env_file}")
        env_loaded = True
        break

if not env_loaded:
    print(f"[Alembic] Warning: .env file not found. Searched:")
    for p in env_candidates:
        print(f"  - {p}")

# ── install.lock decryption (AES-256-GCM, compatible with Go side) ──────────

def _lock_encrypt_key(app_secret: str) -> bytes:
    """Derive the AES-256-GCM key, matching Go's lockEncryptKey."""
    h = hmac.new(app_secret.encode('utf-8'), b'chiron-install-lock-key', hashlib.sha256)
    return h.digest()  # 32 bytes

def _decrypt_from_install_lock(app_secret: str) -> str | None:
    """Read install.lock, decrypt the dsn field, return the plaintext DSN."""
    lock_path = project_root / 'data' / 'install.lock'
    if not lock_path.exists():
        return None
    try:
        data = json.loads(lock_path.read_text(encoding='utf-8'))
    except Exception:
        return None
    enc_dsn = data.get('dsn') if isinstance(data, dict) else None
    if not enc_dsn:
        return None
    # Go's base64.RawStdEncoding: standard alphabet, no padding
    try:
        raw = base64.b64decode(enc_dsn + '==')  # add padding for Python's decoder
    except Exception:
        try:
            raw = base64.b64decode(enc_dsn)  # try without padding
        except Exception:
            return None
    key = _lock_encrypt_key(app_secret)
    # AES-256-GCM: nonce is first 12 bytes
    nonce = raw[:12]
    ct = raw[12:]
    try:
        aesgcm = AESGCM(key)
        plain = aesgcm.decrypt(nonce, ct, None)
        return plain.decode('utf-8')
    except Exception:
        return None

def get_database_url() -> str | None:
    """Resolve database URL from DATABASE_DSN env → install.lock → alembic.ini fallback."""
    # 1) DATABASE_DSN environment variable (highest priority)
    db_dsn = os.getenv("DATABASE_DSN")
    if db_dsn:
        return db_dsn

    # 2) install.lock decryption (requires APP_SECRET)
    app_secret = os.getenv("APP_SECRET")
    if app_secret:
        dsn = _decrypt_from_install_lock(app_secret)
        if dsn:
            print("[Alembic] Decrypted DSN from install.lock")
            return dsn

    # 3) alembic.ini fallback
    fallback = config.get_main_option("sqlalchemy.url")
    if fallback:
        print(f"[Alembic] Using fallback URL from alembic.ini")
        return fallback

    return None

# Set the database URL
db_url = get_database_url()
# 隐藏密码打印
safe_url = "(none)"
if db_url:
    if '@' in db_url:
        parts = db_url.split('@')
        prefix = parts[0]
        suffix = parts[1]
        if ':' in prefix.split('://', 1)[-1]:
            user_part = prefix.split('://', 1)[0] + '://' + prefix.split('://', 1)[-1].split(':')[0]
            safe_url = f"{user_part}:***@{suffix}"
        else:
            safe_url = db_url
    else:
        safe_url = db_url
print(f"[Alembic] Database URL: {safe_url}")
if db_url:
    # Ensure postgresql:// prefix for SQLAlchemy
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    
    # URL-encode the password if it contains special characters
    # Use regex to extract and re-encode the password portion
    from urllib.parse import quote
    import re
    
    try:
        # Match pattern: postgresql://user:password@host...
        # Use greedy match for password to handle @ in password
        # The last @ before host is the separator
        match = re.match(r'(postgresql://[^:]+:)(.+)(@[^@]+:\d+/.+)', db_url)
        if match:
            prefix = match.group(1)  # postgresql://user:
            raw_password = match.group(2)  # raw password (may contain @ and other special chars)
            suffix = match.group(3)  # @host:port/db?params
            
            # URL-encode the password
            from urllib.parse import quote
            encoded_password = quote(raw_password, safe='')
            db_url = prefix + encoded_password + suffix
            print(f"[Alembic] Password URL-encoded successfully")
        else:
            # Try simpler pattern without port
            match = re.match(r'(postgresql://[^:]+:)(.+)(@[^@:]+\..+)', db_url)
            if match:
                prefix = match.group(1)
                raw_password = match.group(2)
                suffix = match.group(3)
                
                from urllib.parse import quote
                encoded_password = quote(raw_password, safe='')
                db_url = prefix + encoded_password + suffix
                print(f"[Alembic] Password URL-encoded successfully (simple pattern)")
            else:
                print(f"[Alembic] Warning: Could not parse URL structure for password encoding")
                print(f"[Alembic] Debug: db_url = {db_url}")
    except Exception as e:
        print(f"[Alembic] Warning: Failed to encode URL: {e}")
    
    config.set_main_option("sqlalchemy.url", db_url)

# add your model's MetaData object here
# for 'autogenerate' support
import sys

# 添加项目根目录到路径
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 导入 Base
from shared.models import Base
target_metadata = Base.metadata

# ============================================================
# 自动发现并加载所有 ORM 模型模块
# 懒加载模式下，仅 import Base 不会触发模型类的加载，
# 需要显式导入所有模型模块才能注册到 Base.metadata
#
# 策略：从 shared.models 的 _LAZY_IMPORTS 字典自动获取所有模型，
# 无需手动维护模型列表（每次 generate-all 后自动同步）
# ============================================================
import importlib
import re

_loaded_count = 0
_failed_count = 0

# 策略 1: 从 _LAZY_IMPORTS 字典自动加载（由代码生成器维护）
try:
    from shared.models import _LAZY_IMPORTS

    for _model_name, _module_path in _LAZY_IMPORTS.items():
        try:
            _mod = importlib.import_module(_module_path, package='shared.models')
            # 触发类加载以注册到 Base.metadata
            getattr(_mod, _model_name)
            _loaded_count += 1
        except Exception as e:
            _failed_count += 1
            print(f"[Alembic] Warning: Could not load {_model_name} from {_module_path}: {e}")
except ImportError:
    print("[Alembic] Warning: _LAZY_IMPORTS not found, falling back to directory scan")

# 策略 2: 扫描 shared/models/ 目录中的手动模型文件（未在 _LAZY_IMPORTS 中注册的）
_shared_models_dir = project_root / "shared" / "models"
_known_modules = set()
if '_LAZY_IMPORTS' in dir():
    _known_modules = {v.lstrip('.') for v in _LAZY_IMPORTS.values()}

for _py_file in sorted(_shared_models_dir.rglob("*.py")):
    if _py_file.name.startswith('_') or _py_file.name == '__init__.py':
        continue
    try:
        _content = _py_file.read_text(encoding='utf-8')
    except (UnicodeDecodeError, OSError):
        continue
    # 只处理包含 class XXX(Base): 的文件
    if 'from . import Base' not in _content.replace(' ', '') and 'from shared.models' not in _content:
        if not re.search(r'class\s+\w+\s*\([^)]*Base[^)]*\)\s*:', _content):
            continue
    # 计算模块路径
    _rel_path = _py_file.relative_to(_shared_models_dir)
    _module_dot = '.'.join(_rel_path.with_suffix('').parts)
    _full_module = f"shared.models.{_module_dot}"
    if _module_dot in _known_modules or _full_module in _known_modules:
        continue
    try:
        importlib.import_module(f".{_module_dot}", package='shared.models')
        _loaded_count += 1
    except Exception as e:
        _failed_count += 1
        print(f"[Alembic] Warning: Could not load {_full_module}: {e}")

print(f"[Alembic] Loaded {_loaded_count} model modules ({_failed_count} failed)")
print(f"[Alembic] Registered {len(target_metadata.tables)} tables in metadata")

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # 比较列类型
            render_as_batch=True,  # 支持批量操作（SQLite需要）
            include_schemas=True,  # 包含所有schema
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
