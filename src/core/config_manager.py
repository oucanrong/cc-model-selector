# 路径: src/core/config_manager.py
# 作用: 修复 provider 切换时 base_url 错误问题，取消 base_url/token 必须同时非空校验

from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

from .constants import (
    CONFIG_PATH,
    DEFAULT_PROVIDER,
    DEFAULT_MODEL,
    DEFAULT_OPUS_MODEL,
    DEFAULT_SONNET_MODEL,
    DEFAULT_HAIKU_MODEL,
    DEFAULT_SUBAGENT_MODEL,
    DEFAULT_EFFORT_LEVEL,
    DEFAULT_RECENT_PROJECTS,
    PROVIDER_OPTIONS,
    get_provider_preset,
)


@dataclass
class ProxyItem:
    enabled: bool = False
    host: str = ""
    port: str = ""
    auth: str = ""


@dataclass
class ProxyConfig:
    http: ProxyItem = field(default_factory=ProxyItem)
    https: ProxyItem = field(default_factory=ProxyItem)
    socks5: ProxyItem = field(default_factory=ProxyItem)


@dataclass
class ProviderSettings:
    base_url: str = ""
    token: str = ""
    anthropic_model: str = ""
    default_opus_model: str = ""
    default_sonnet_model: str = ""
    default_haiku_model: str = ""
    subagent_model: str = ""
    effort_level: str = ""
    # Kimi 专用
    enable_tool_search: str = "false"
    # GML5 专用
    disable_nonessential_traffic: str = "1"
    api_timeout_ms: str = "3000000"
    proxy: ProxyConfig = field(default_factory=ProxyConfig)


@dataclass
class AppConfig:
    provider: str = DEFAULT_PROVIDER
    base_url: str = ""
    token: str = ""
    auth_tokens: dict[str, str] = field(default_factory=dict)
    anthropic_model: str = DEFAULT_MODEL
    default_opus_model: str = DEFAULT_OPUS_MODEL
    default_sonnet_model: str = DEFAULT_SONNET_MODEL
    default_haiku_model: str = DEFAULT_HAIKU_MODEL
    subagent_model: str = DEFAULT_SUBAGENT_MODEL
    effort_level: str = DEFAULT_EFFORT_LEVEL
    # Kimi 专用
    enable_tool_search: str = "false"
    # GML5 专用
    disable_nonessential_traffic: str = "1"
    api_timeout_ms: str = "3000000"
    project_path: str = ""
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    recent_projects: list[str] = field(default_factory=list)
    provider_settings: dict[str, ProviderSettings] = field(default_factory=dict)


class ConfigManager:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or CONFIG_PATH

    def load(self) -> AppConfig:
        if not self.path.exists():
            return AppConfig()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return AppConfig()
        config = self._from_dict(data)
        provider = config.provider if config.provider in PROVIDER_OPTIONS else DEFAULT_PROVIDER
        config.provider = provider
        self._sync_active_provider(config)
        return config

    def save(self, config: AppConfig) -> None:
        self._flush_active_provider(config)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._to_dict(config), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _sync_active_provider(self, config: AppConfig) -> None:
        preset = get_provider_preset(config.provider)
        ps = config.provider_settings.get(config.provider)
        if ps is None:
            ps = ProviderSettings(
                base_url="",
                token="",
                anthropic_model="",
                default_opus_model="",
                default_sonnet_model="",
                default_haiku_model="",
                subagent_model="",
                effort_level="",
                proxy=ProxyConfig(),
            )
            config.provider_settings[config.provider] = ps

        # 保证 base_url 使用 provider_settings 中保存的值，否则使用预设
        config.base_url = ps.base_url or preset.base_url
        config.token = ps.token or ""
        config.anthropic_model = ps.anthropic_model or preset.anthropic_model_default
        config.default_opus_model = ps.default_opus_model or preset.default_opus_model_default
        config.default_sonnet_model = ps.default_sonnet_model or preset.default_sonnet_model_default
        config.default_haiku_model = ps.default_haiku_model or preset.default_haiku_model_default
        config.subagent_model = ps.subagent_model or preset.subagent_model_default
        config.effort_level = ps.effort_level or preset.effort_level_default
        config.proxy = ps.proxy
        # Kimi 专用参数
        config.enable_tool_search = ps.enable_tool_search or preset.enable_tool_search_default
        # GML5 专用参数
        config.disable_nonessential_traffic = ps.disable_nonessential_traffic or preset.disable_nonessential_traffic_default
        config.api_timeout_ms = ps.api_timeout_ms or preset.api_timeout_ms_default

    def _flush_active_provider(self, config: AppConfig) -> None:
        token = config.token.strip()
        config.auth_tokens[config.provider] = token
        ps = ProviderSettings(
            base_url=config.base_url,
            token=token,
            anthropic_model=config.anthropic_model,
            default_opus_model=config.default_opus_model,
            default_sonnet_model=config.default_sonnet_model,
            default_haiku_model=config.default_haiku_model,
            subagent_model=config.subagent_model,
            effort_level=config.effort_level,
            enable_tool_search=config.enable_tool_search,
            disable_nonessential_traffic=config.disable_nonessential_traffic,
            api_timeout_ms=config.api_timeout_ms,
            proxy=config.proxy,
        )
        config.provider_settings[config.provider] = ps

    def _from_dict(self, data: dict[str, Any]) -> AppConfig:
        provider = data.get("provider", DEFAULT_PROVIDER)
        if provider not in PROVIDER_OPTIONS:
            provider = DEFAULT_PROVIDER
        auth_tokens = {p: str(data.get("auth_tokens", {}).get(p, "") or "") for p in PROVIDER_OPTIONS}
        provider_settings = {}
        for p, v in (data.get("provider_settings") or {}).items():
            provider_settings[p] = ProviderSettings(
                base_url=str(v.get("base_url", "") or ""),
                token=str(v.get("token", "") or ""),
                anthropic_model=str(v.get("anthropic_model", "") or ""),
                default_opus_model=str(v.get("default_opus_model", "") or ""),
                default_sonnet_model=str(v.get("default_sonnet_model", "") or ""),
                default_haiku_model=str(v.get("default_haiku_model", "") or ""),
                subagent_model=str(v.get("subagent_model", "") or ""),
                effort_level=str(v.get("effort_level", "") or ""),
                enable_tool_search=str(v.get("enable_tool_search", "") or "false"),
                disable_nonessential_traffic=str(v.get("disable_nonessential_traffic", "") or "1"),
                api_timeout_ms=str(v.get("api_timeout_ms", "") or "3000000"),
            )
        # 初始化不存在 provider 的条目
        for p in PROVIDER_OPTIONS:
            if p not in provider_settings:
                preset = get_provider_preset(p)
                provider_settings[p] = ProviderSettings(
                    base_url="",
                    token=auth_tokens.get(p, ""),
                    anthropic_model=preset.anthropic_model_default,
                    default_opus_model=preset.default_opus_model_default,
                    default_sonnet_model=preset.default_sonnet_model_default,
                    default_haiku_model=preset.default_haiku_model_default,
                    subagent_model=preset.subagent_model_default,
                    effort_level=preset.effort_level_default,
                )
        return AppConfig(
            provider=provider,
            base_url=str(data.get("base_url", "") or ""),
            token=auth_tokens.get(provider, ""),
            auth_tokens=auth_tokens,
            anthropic_model=str(data.get("anthropic_model", "") or ""),
            default_opus_model=str(data.get("default_opus_model", "") or ""),
            default_sonnet_model=str(data.get("default_sonnet_model", "") or ""),
            default_haiku_model=str(data.get("default_haiku_model", "") or ""),
            subagent_model=str(data.get("subagent_model", "") or ""),
            effort_level=str(data.get("effort_level", "") or ""),
            enable_tool_search=str(data.get("enable_tool_search", "") or "false"),
            disable_nonessential_traffic=str(data.get("disable_nonessential_traffic", "") or "1"),
            api_timeout_ms=str(data.get("api_timeout_ms", "") or "3000000"),
            project_path=str(data.get("project_path", "") or ""),
            proxy=ProxyConfig(),
            recent_projects=data.get("recent_projects", []) or [],
            provider_settings=provider_settings,
        )

    def _to_dict(self, config: AppConfig) -> dict[str, Any]:
        ps_dict = {}
        for p in PROVIDER_OPTIONS:
            ps = config.provider_settings.get(p, ProviderSettings())
            ps_dict[p] = {
                "base_url": ps.base_url,
                "token": ps.token,
                "anthropic_model": ps.anthropic_model,
                "default_opus_model": ps.default_opus_model,
                "default_sonnet_model": ps.default_sonnet_model,
                "default_haiku_model": ps.default_haiku_model,
                "subagent_model": ps.subagent_model,
                "effort_level": ps.effort_level,
                "enable_tool_search": ps.enable_tool_search,
                "disable_nonessential_traffic": ps.disable_nonessential_traffic,
                "api_timeout_ms": ps.api_timeout_ms,
            }
        return {
            "provider": config.provider,
            "auth_tokens": config.auth_tokens,
            "project_path": config.project_path,
            "recent_projects": config.recent_projects[:DEFAULT_RECENT_PROJECTS],
            "provider_settings": ps_dict,
        }
