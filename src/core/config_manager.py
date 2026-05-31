# 路径: src/core/config_manager.py
# 作用: 配置读写管理，支持每个 Provider 独立存储所有参数（含 base_url 与代理）

from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

from .constants import (
    CONFIG_PATH,
    DEFAULT_BASE_URL,
    DEFAULT_EFFORT_LEVEL,
    DEFAULT_HAIKU_MODEL,
    DEFAULT_MODEL,
    DEFAULT_OPUS_MODEL,
    DEFAULT_PROVIDER,
    DEFAULT_RECENT_PROJECTS,
    DEFAULT_SONNET_MODEL,
    DEFAULT_SUBAGENT_MODEL,
    PROVIDER_CLAUDE_DEFAULT,
    PROVIDER_CLAUDE_RELAY,
    PROVIDER_DEEPSEEK,
    PROVIDER_GPT_RELAY,
    PROVIDER_KIMI,
    PROVIDER_OPTIONS,
    PROVIDER_ZHIPU,
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
    """单个 Provider 的全部参数快照（含 base_url、token、模型、代理）。"""
    base_url: str = ""
    token: str = ""
    anthropic_model: str = ""
    default_opus_model: str = ""
    default_sonnet_model: str = ""
    default_haiku_model: str = ""
    subagent_model: str = ""
    effort_level: str = ""
    proxy: ProxyConfig = field(default_factory=ProxyConfig)


@dataclass
class AppConfig:
    provider: str = DEFAULT_PROVIDER
    # ---- 当前激活 provider 的快捷字段（从 provider_settings 同步而来） ----
    base_url: str = DEFAULT_BASE_URL
    token: str = ""
    auth_tokens: dict[str, str] = field(default_factory=dict)
    anthropic_model: str = DEFAULT_MODEL
    default_opus_model: str = DEFAULT_OPUS_MODEL
    default_sonnet_model: str = DEFAULT_SONNET_MODEL
    default_haiku_model: str = DEFAULT_HAIKU_MODEL
    subagent_model: str = DEFAULT_SUBAGENT_MODEL
    effort_level: str = DEFAULT_EFFORT_LEVEL
    project_path: str = ""
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    recent_projects: list[str] = field(default_factory=list)
    # ---- 每个 provider 的完整参数快照 ----
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
        # 从 provider_settings 同步当前 provider 快捷字段
        self._sync_active_provider(config)
        return config

    def save(self, config: AppConfig) -> None:
        # 写入前先把当前快捷字段同步回 provider_settings
        self._flush_active_provider(config)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._to_dict(config), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _sync_active_provider(self, config: AppConfig) -> None:
        """从 provider_settings 把当前 provider 的数据写入快捷字段。"""
        ps = config.provider_settings.get(config.provider)
        if ps is None:
            # 使用预设值填充默认值
            preset = get_provider_preset(config.provider)
            config.base_url = config.base_url or preset.base_url
            config.token = config.auth_tokens.get(config.provider, "").strip()
            return

        preset = get_provider_preset(config.provider)
        config.base_url = ps.base_url or preset.base_url
        config.token = ps.token.strip()
        config.auth_tokens[config.provider] = ps.token.strip()
        config.anthropic_model = ps.anthropic_model or preset.anthropic_model_default
        config.default_opus_model = ps.default_opus_model or preset.default_opus_model_default
        config.default_sonnet_model = ps.default_sonnet_model or preset.default_sonnet_model_default
        config.default_haiku_model = ps.default_haiku_model or preset.default_haiku_model_default
        config.subagent_model = ps.subagent_model or preset.subagent_model_default
        config.effort_level = ps.effort_level or preset.effort_level_default
        config.proxy = ps.proxy

    def _flush_active_provider(self, config: AppConfig) -> None:
        """把当前快捷字段写回 provider_settings，并同步 auth_tokens。"""
        # 同步 token 到 auth_tokens
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
            proxy=config.proxy,
        )
        config.provider_settings[config.provider] = ps

    def _normalize_auth_tokens(self, data: Any) -> dict[str, str]:
        if not isinstance(data, dict):
            return {}
        result: dict[str, str] = {}
        for key, value in data.items():
            if value is None:
                result[str(key)] = ""
            else:
                result[str(key)] = str(value)
        return result

    def _parse_proxy(self, proxy_data: dict) -> ProxyConfig:
        def _item(d: Any) -> ProxyItem:
            if not isinstance(d, dict):
                return ProxyItem()
            return ProxyItem(
                enabled=bool(d.get("enabled", False)),
                host=str(d.get("host", "") or ""),
                port=str(d.get("port", "") or ""),
                auth=str(d.get("auth", "") or ""),
            )
        return ProxyConfig(
            http=_item(proxy_data.get("http", {})),
            https=_item(proxy_data.get("https", {})),
            socks5=_item(proxy_data.get("socks5", {})),
        )

    def _parse_provider_settings(self, raw: Any) -> dict[str, ProviderSettings]:
        if not isinstance(raw, dict):
            return {}
        result: dict[str, ProviderSettings] = {}
        for provider_key, v in raw.items():
            if not isinstance(v, dict):
                continue
            result[provider_key] = ProviderSettings(
                base_url=str(v.get("base_url", "") or ""),
                token=str(v.get("token", "") or ""),
                anthropic_model=str(v.get("anthropic_model", "") or ""),
                default_opus_model=str(v.get("default_opus_model", "") or ""),
                default_sonnet_model=str(v.get("default_sonnet_model", "") or ""),
                default_haiku_model=str(v.get("default_haiku_model", "") or ""),
                subagent_model=str(v.get("subagent_model", "") or ""),
                effort_level=str(v.get("effort_level", "") or ""),
                proxy=self._parse_proxy(v.get("proxy", {})),
            )
        return result

    def _from_dict(self, data: dict[str, Any]) -> AppConfig:
        provider = data.get("provider", DEFAULT_PROVIDER)
        if provider not in PROVIDER_OPTIONS:
            provider = DEFAULT_PROVIDER

        proxy_data = data.get("proxy", {})
        auth_tokens = self._normalize_auth_tokens(data.get("auth_tokens", {}))
        legacy_token = str(data.get("token", "") or "").strip()

        if not auth_tokens and legacy_token:
            auth_tokens = {provider: legacy_token}
        elif legacy_token and not auth_tokens.get(provider, "").strip():
            auth_tokens[provider] = legacy_token

        # 解析 provider_settings
        provider_settings = self._parse_provider_settings(data.get("provider_settings", {}))

        # 兼容旧格式：若 provider_settings 中没有当前 provider 的条目，
        # 则从顶层字段 + auth_tokens 中迁移数据
        if provider not in provider_settings:
            preset = get_provider_preset(provider)
            provider_settings[provider] = ProviderSettings(
                base_url=str(data.get("base_url", preset.base_url) or preset.base_url),
                token=auth_tokens.get(provider, "").strip(),
                anthropic_model=str(data.get("anthropic_model", preset.anthropic_model_default) or ""),
                default_opus_model=str(data.get("default_opus_model", preset.default_opus_model_default) or ""),
                default_sonnet_model=str(data.get("default_sonnet_model", preset.default_sonnet_model_default) or ""),
                default_haiku_model=str(data.get("default_haiku_model", preset.default_haiku_model_default) or ""),
                subagent_model=str(data.get("subagent_model", preset.subagent_model_default) or ""),
                effort_level=str(data.get("effort_level", preset.effort_level_default) or ""),
                proxy=self._parse_proxy(proxy_data),
            )

        # 从顶层字段还原其他已存在 provider 的 auth_tokens（兼容旧 auth_tokens 字段）
        for p, tok in auth_tokens.items():
            if p in provider_settings:
                if not provider_settings[p].token.strip() and tok.strip():
                    provider_settings[p].token = tok.strip()
            else:
                # 仅有 token 记录，补建一个最小条目
                preset = get_provider_preset(p)
                provider_settings[p] = ProviderSettings(
                    base_url=preset.base_url,
                    token=tok.strip(),
                )

        return AppConfig(
            provider=provider,
            base_url=str(data.get("base_url", DEFAULT_BASE_URL) or ""),
            token=auth_tokens.get(provider, legacy_token),
            auth_tokens=auth_tokens,
            anthropic_model=str(data.get("anthropic_model", DEFAULT_MODEL) or ""),
            default_opus_model=str(data.get("default_opus_model", DEFAULT_OPUS_MODEL) or ""),
            default_sonnet_model=str(data.get("default_sonnet_model", DEFAULT_SONNET_MODEL) or ""),
            default_haiku_model=str(data.get("default_haiku_model", DEFAULT_HAIKU_MODEL) or ""),
            subagent_model=str(data.get("subagent_model", DEFAULT_SUBAGENT_MODEL) or ""),
            effort_level=str(data.get("effort_level", DEFAULT_EFFORT_LEVEL) or ""),
            project_path=str(data.get("project_path", "") or ""),
            proxy=self._parse_proxy(proxy_data),
            recent_projects=data.get("recent_projects", []),
            provider_settings=provider_settings,
        )

    def _to_dict(self, config: AppConfig) -> dict[str, Any]:
        # 构造 provider_settings 序列化结构（按 PROVIDER_OPTIONS 顺序输出）
        ps_dict: dict[str, Any] = {}
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
                "proxy": {
                    "http": asdict(ps.proxy.http),
                    "https": asdict(ps.proxy.https),
                    "socks5": asdict(ps.proxy.socks5),
                },
            }

        # 向后兼容：保留顶层 auth_tokens 字段
        ordered_auth_tokens = {p: config.provider_settings.get(p, ProviderSettings()).token for p in PROVIDER_OPTIONS}

        return {
            "provider": config.provider,
            "auth_tokens": ordered_auth_tokens,
            "project_path": config.project_path,
            "recent_projects": config.recent_projects[:DEFAULT_RECENT_PROJECTS],
            "provider_settings": ps_dict,
        }
