"""Prompt 版本管理 — 版本化 Prompt 模板，支持 A/B 测试。

典型用法：
    mgr = PromptManager()
    mgr.create("system_v1", "You are a helpful assistant...", tags=["default"])
    mgr.create("system_v2", "You are a knowledgeable AI...", tags=["ab_test"], parent="system_v1")
    active = mgr.resolve("system_v1")  # 返回最新版本
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    """Prompt 模板（不含版本信息的逻辑模板）。"""
    name: str
    template: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PromptVersion:
    """Prompt 的某个版本。"""
    id: str
    template_name: str
    version: int
    content: str
    parent_version_id: str | None = None
    tags: list[str] = field(default_factory=list)
    note: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


class PromptManager:
    """Prompt 版本管理器（进程内，生产环境应替换为 DB 持久化）。"""

    def __init__(self):
        self._templates: dict[str, PromptTemplate] = {}
        self._versions: dict[str, list[PromptVersion]] = {}  # template_name -> [versions]

    def register_template(self, template: PromptTemplate) -> None:
        """注册一个 Prompt 模板。"""
        self._templates[template.name] = template

    def create(self, template_name: str, content: str, *, note: str = "", tags: list[str] | None = None, parent: str | None = None) -> PromptVersion:
        """创建新版本。"""
        if template_name not in self._templates:
            raise ValueError(f"Template '{template_name}' not registered")
        versions = self._versions.setdefault(template_name, [])
        version_num = len(versions) + 1
        pv = PromptVersion(
            id=str(uuid.uuid4()),
            template_name=template_name,
            version=version_num,
            content=content,
            parent_version_id=parent,
            tags=tags or [],
            note=note,
        )
        versions.append(pv)
        return pv

    def get_latest(self, template_name: str) -> PromptVersion | None:
        """获取模板的最新版本。"""
        versions = self._versions.get(template_name)
        if not versions:
            return None
        return versions[-1]

    def get_version(self, template_name: str, version: int) -> PromptVersion | None:
        """获取指定版本。"""
        versions = self._versions.get(template_name)
        if not versions:
            return None
        for v in versions:
            if v.version == version:
                return v
        return None

    def list_versions(self, template_name: str) -> list[PromptVersion]:
        """列出模板的所有版本。"""
        return self._versions.get(template_name, [])

    def resolve(self, template_name: str, tag: str | None = None) -> str | None:
        """解析模板到最新匹配版本的内容。

        Args:
            template_name: 模板名称
            tag: 可选标签，如果指定则返回匹配该标签的最新版本

        Returns:
            str: 渲染后的 Prompt 内容，找不到返回 None
        """
        versions = self._versions.get(template_name)
        if not versions:
            return None
        if tag:
            for v in reversed(versions):
                if tag in v.tags:
                    return v.content
        return versions[-1].content

    def to_dict(self) -> dict[str, Any]:
        """导出所有模板和版本（用于持久化）。"""
        return {
            "templates": {n: {"name": t.name, "description": t.description, "tags": t.tags} for n, t in self._templates.items()},
            "versions": {
                n: [
                    {"id": v.id, "version": v.version, "content": v.content, "tags": v.tags, "note": v.note, "created_at": v.created_at.isoformat()}
                    for v in vs
                ]
                for n, vs in self._versions.items()
            },
        }