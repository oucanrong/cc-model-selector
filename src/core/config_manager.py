# 路径: C:\Users\oucan\Documents\vscode\claude_code启动器\src\core\config_manager.py
# 作用: 修复 provider 切换时代理配置互相干扰的问题，确保各 provider 配置完全独立

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

from .constants import (
    CLAUDE_LAUNCH_TARGET_DEFAULT,
    CLAUDE_LAUNCH_TARGET_OPTIONS,
    CODEX_PROVIDER_DEFAULTS,
    CODEX_LAUNCH_TARGET_DEFAULT,
    CODEX_LAUNCH_TARGET_OPTIONS,
    CODEX_PROVIDER_OFFICIAL,
    CODEX_PROVIDER_OPTIONS,
    CONFIG_PATH,
    DEFAULT_PROVIDER,
    DEFAULT_MODEL,
    DEFAULT_OPUS_MODEL,
    DEFAULT_SONNET_MODEL,
    DEFAULT_HAIKU_MODEL,
    DEFAULT_SUBAGENT_MODEL,
    DEFAULT_EFFORT_LEVEL,
    DEFAULT_RECENT_PROJECTS,
    PROVIDER_MINIMAX,
    PROVIDER_OPTIONS,
    get_codex_reasoning_defaults,
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


def create_claude_target_proxies() -> dict[str, ProxyConfig]:
    return {
        target: ProxyConfig()
        for target, _label in CLAUDE_LAUNCH_TARGET_OPTIONS
    }


def create_codex_target_proxies() -> dict[str, ProxyConfig]:
    return {
        target: ProxyConfig()
        for target, _label in CODEX_LAUNCH_TARGET_OPTIONS
    }


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
    # GLM5 专用
    disable_nonessential_traffic: str = "1"
    api_timeout_ms: str = "3000000"
    # 小米MiMo / 方舟Coding Plan 专用
    has_completed_onboarding: str = "true"
    proxies: dict[str, ProxyConfig] = field(default_factory=create_claude_target_proxies)
    proxy: ProxyConfig = field(default_factory=ProxyConfig, repr=False, compare=False)


@dataclass
class CodexModelReasoningSettings:
    reasoning_effort: str = ""
    thinking_enabled: bool = False


@dataclass
class CodexProviderSettings:
    base_url: str = ""
    token: str = ""
    model: str = ""
    reasoning_effort: str = ""
    thinking_enabled: bool = True
    model_reasoning: dict[str, CodexModelReasoningSettings] = field(
        default_factory=dict
    )
    proxies: dict[str, ProxyConfig] = field(default_factory=create_codex_target_proxies)
    proxy: ProxyConfig = field(default_factory=ProxyConfig, repr=False, compare=False)


@dataclass
class CodexConfig:
    provider: str = CODEX_PROVIDER_OFFICIAL
    launch_target: str = CODEX_LAUNCH_TARGET_DEFAULT
    project_path: str = ""
    recent_projects: list[str] = field(default_factory=list)
    provider_settings: dict[str, CodexProviderSettings] = field(default_factory=dict)


def create_default_codex_config() -> CodexConfig:
    settings = {}
    for provider_name in CODEX_PROVIDER_OPTIONS:
        defaults = CODEX_PROVIDER_DEFAULTS[provider_name]
        model_reasoning = {}
        for model in defaults.get("model_reasoning", {}):
            reasoning = get_codex_reasoning_defaults(provider_name, model)
            model_reasoning[model] = CodexModelReasoningSettings(
                reasoning_effort=str(reasoning["default_reasoning_effort"]),
                thinking_enabled=bool(reasoning["default_thinking_enabled"]),
            )
        selected_reasoning = get_codex_reasoning_defaults(
            provider_name,
            str(defaults["default_model"]),
        )
        settings[provider_name] = CodexProviderSettings(
            base_url=str(defaults["base_url"]),
            model=str(defaults["default_model"]),
            reasoning_effort=str(selected_reasoning["default_reasoning_effort"]),
            thinking_enabled=bool(selected_reasoning["default_thinking_enabled"]),
            model_reasoning=model_reasoning,
        )
    return CodexConfig(provider_settings=settings)


@dataclass
class AppConfig:
    provider: str = DEFAULT_PROVIDER
    claude_launch_target: str = CLAUDE_LAUNCH_TARGET_DEFAULT
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
    # GLM5 专用
    disable_nonessential_traffic: str = "1"
    api_timeout_ms: str = "3000000"
    # 小米MiMo / 方舟Coding Plan 专用
    has_completed_onboarding: str = "true"
    project_path: str = ""
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    recent_projects: list[str] = field(default_factory=list)
    vscode_path: str = ""
    provider_settings: dict[str, ProviderSettings] = field(default_factory=dict)
    codex: CodexConfig = field(default_factory=create_default_codex_config)


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
        codex_setting = config.codex.provider_settings.get(config.codex.provider)
        if codex_setting is not None:
            codex_setting.proxies[config.codex.launch_target] = copy.deepcopy(
                codex_setting.proxy
            )
            codex_setting.proxies["desktop"] = ProxyConfig()
            codex_setting.proxies["vscode"] = ProxyConfig()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._to_dict(config), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _sync_active_provider(self, config: AppConfig) -> None:
        """将 provider_settings 中当前 provider 的配置同步到 config 顶层字段。"""
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
        config.proxy = copy.deepcopy(
            ps.proxies.get(config.claude_launch_target, ProxyConfig())
        )
        ps.proxy = copy.deepcopy(config.proxy)
        # Kimi 专用参数
        config.enable_tool_search = ps.enable_tool_search or preset.enable_tool_search_default
        # GLM5 专用参数
        config.disable_nonessential_traffic = ps.disable_nonessential_traffic or preset.disable_nonessential_traffic_default
        config.api_timeout_ms = ps.api_timeout_ms or preset.api_timeout_ms_default
        # 小米MiMo / 方舟Coding Plan 专用参数
        config.has_completed_onboarding = ps.has_completed_onboarding or preset.has_completed_onboarding_default

    def _flush_active_provider(self, config: AppConfig) -> None:
        """将 config 顶层字段写回 provider_settings 中当前 provider 的条目。"""
        token = config.token.strip()
        config.auth_tokens[config.provider] = token
        existing = config.provider_settings.get(
            config.provider,
            ProviderSettings(),
        )
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
            has_completed_onboarding=config.has_completed_onboarding,
            proxies=copy.deepcopy(existing.proxies),
        )
        ps.proxies[config.claude_launch_target] = copy.deepcopy(config.proxy)
        ps.proxies["vscode"] = ProxyConfig()
        ps.proxy = copy.deepcopy(config.proxy)
        config.provider_settings[config.provider] = ps

    def _from_dict(self, data: dict[str, Any]) -> AppConfig:
        self._migrate_minimax_name(data)
        self._migrate_codex_ark_name(data)
        provider = data.get("provider", DEFAULT_PROVIDER)
        if provider not in PROVIDER_OPTIONS:
            provider = DEFAULT_PROVIDER
        auth_tokens = {p: str(data.get("auth_tokens", {}).get(p, "") or "") for p in PROVIDER_OPTIONS}
        provider_settings = {}
        for p, v in (data.get("provider_settings") or {}).items():
            proxies = create_claude_target_proxies()
            for target, proxy_data in (v.get("proxies") or {}).items():
                if target not in proxies or target == "vscode":
                    continue
                proxies[target] = ProxyConfig(
                    http=ProxyItem(**(proxy_data.get("http") or {})),
                    https=ProxyItem(**(proxy_data.get("https") or {})),
                    socks5=ProxyItem(**(proxy_data.get("socks5") or {})),
                )
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
                has_completed_onboarding=str(v.get("has_completed_onboarding", "") or "true"),
                proxies=proxies,
            )
        # 为 JSON 中不存在的 provider 初始化默认条目，每个 provider 获得独立的 ProxyConfig
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
                    # proxy 使用 default_factory 自动创建独立实例
                )
        codex_data = data.get("codex") or {}
        claude_launch_targets = {value for value, _ in CLAUDE_LAUNCH_TARGET_OPTIONS}
        claude_launch_target = str(
            data.get("claude_launch_target", CLAUDE_LAUNCH_TARGET_DEFAULT) or ""
        )
        if claude_launch_target not in claude_launch_targets:
            claude_launch_target = CLAUDE_LAUNCH_TARGET_DEFAULT
        codex_launch_targets = {value for value, _ in CODEX_LAUNCH_TARGET_OPTIONS}
        codex_launch_target = str(
            codex_data.get("launch_target", CODEX_LAUNCH_TARGET_DEFAULT) or ""
        )
        if codex_launch_target not in codex_launch_targets:
            codex_launch_target = CODEX_LAUNCH_TARGET_DEFAULT
        codex_provider = str(codex_data.get("provider", CODEX_PROVIDER_OFFICIAL) or "")
        if codex_provider not in CODEX_PROVIDER_OPTIONS:
            codex_provider = CODEX_PROVIDER_OFFICIAL
        codex_settings: dict[str, CodexProviderSettings] = {}
        raw_codex_settings = codex_data.get("provider_settings") or {}
        for provider_name in CODEX_PROVIDER_OPTIONS:
            raw = raw_codex_settings.get(provider_name) or {}
            defaults = CODEX_PROVIDER_DEFAULTS[provider_name]
            model = str(raw.get("model", "") or defaults["default_model"])
            selected_defaults = get_codex_reasoning_defaults(provider_name, model)
            reasoning_options = selected_defaults["reasoning_options"]
            raw_reasoning_effort = str(
                raw.get("reasoning_effort", "")
                or selected_defaults["default_reasoning_effort"]
            )
            effort_map = selected_defaults.get("chat_reasoning", {}).get(
                "effort_map",
                {},
            )
            reasoning_effort = effort_map.get(
                raw_reasoning_effort,
                raw_reasoning_effort,
            )
            if reasoning_effort not in reasoning_options:
                reasoning_effort = str(
                    selected_defaults["default_reasoning_effort"]
                )
            model_reasoning = {}
            raw_model_reasoning = raw.get("model_reasoning") or {}
            for model_name in defaults.get("model_reasoning", {}):
                model_defaults = get_codex_reasoning_defaults(
                    provider_name,
                    model_name,
                )
                raw_model = raw_model_reasoning.get(model_name) or {}
                model_options = model_defaults["reasoning_options"]
                legacy_model_effort = str(
                    raw_model.get("reasoning_effort", "")
                )
                model_effort = str(
                    legacy_model_effort
                    or model_defaults["default_reasoning_effort"]
                )
                if model_effort not in model_options:
                    model_effort = str(
                        model_defaults["default_reasoning_effort"]
                    )
                thinking_enabled = (
                    bool(raw_model.get("thinking_enabled"))
                    if "thinking_enabled" in raw_model
                    else bool(model_defaults["default_thinking_enabled"])
                )
                if (
                    model_name.startswith("deepseek-v4-")
                    and legacy_model_effort
                ):
                    thinking_enabled = legacy_model_effort not in {
                        "minimal",
                        "none",
                        "off",
                        "disabled",
                    }
                model_reasoning[model_name] = CodexModelReasoningSettings(
                    reasoning_effort=model_effort if model_options else "",
                    thinking_enabled=thinking_enabled,
                )
            selected_model_reasoning = model_reasoning.get(model)
            if selected_model_reasoning is not None:
                reasoning_effort = selected_model_reasoning.reasoning_effort
                thinking_enabled = selected_model_reasoning.thinking_enabled
            else:
                thinking_enabled = (
                    bool(raw.get("thinking_enabled"))
                    if "thinking_enabled" in raw
                    else bool(selected_defaults["default_thinking_enabled"])
                )
            proxies = create_codex_target_proxies()
            for target, proxy_data in (raw.get("proxies") or {}).items():
                if target not in proxies or target in {"desktop", "vscode"}:
                    continue
                proxies[target] = ProxyConfig(
                    http=ProxyItem(**(proxy_data.get("http") or {})),
                    https=ProxyItem(**(proxy_data.get("https") or {})),
                    socks5=ProxyItem(**(proxy_data.get("socks5") or {})),
                )
            codex_settings[provider_name] = CodexProviderSettings(
                base_url=str(raw.get("base_url", "") or defaults["base_url"]),
                token=str(raw.get("token", "") or ""),
                model=model,
                reasoning_effort=reasoning_effort if reasoning_options else "",
                thinking_enabled=thinking_enabled,
                model_reasoning=model_reasoning,
                proxies=proxies,
                proxy=copy.deepcopy(proxies[codex_launch_target]),
            )

        return AppConfig(
            provider=provider,
            claude_launch_target=claude_launch_target,
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
            has_completed_onboarding=str(data.get("has_completed_onboarding", "") or "true"),
            project_path=str(data.get("project_path", "") or ""),
            # 顶层 proxy 始终初始化为空——后续由 _sync_active_provider 从
            # provider_settings[provider] 中深拷贝加载当前 provider 的真实代理配置
            proxy=ProxyConfig(),
            recent_projects=data.get("recent_projects", []) or [],
            vscode_path=str(data.get("vscode_path", "") or ""),
            provider_settings=provider_settings,
            codex=CodexConfig(
                provider=codex_provider,
                launch_target=codex_launch_target,
                project_path=str(codex_data.get("project_path", "") or ""),
                recent_projects=codex_data.get("recent_projects", []) or [],
                provider_settings=codex_settings,
            ),
        )

    @staticmethod
    def _migrate_minimax_name(data: dict[str, Any]) -> None:
        legacy = "MINIMAX"
        if data.get("provider") == legacy:
            data["provider"] = PROVIDER_MINIMAX
        auth_tokens = data.get("auth_tokens")
        if isinstance(auth_tokens, dict) and legacy in auth_tokens:
            auth_tokens.setdefault(PROVIDER_MINIMAX, auth_tokens.pop(legacy))
        provider_settings = data.get("provider_settings")
        if isinstance(provider_settings, dict) and legacy in provider_settings:
            provider_settings.setdefault(PROVIDER_MINIMAX, provider_settings.pop(legacy))

    @staticmethod
    def _migrate_codex_ark_name(data: dict[str, Any]) -> None:
        legacy = "方舟 Coding Plan"
        current = "方舟Coding Plan"
        codex = data.get("codex")
        if not isinstance(codex, dict):
            return
        if codex.get("provider") == legacy:
            codex["provider"] = current
        settings = codex.get("provider_settings")
        if isinstance(settings, dict) and legacy in settings:
            settings.setdefault(current, settings.pop(legacy))

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
                "has_completed_onboarding": ps.has_completed_onboarding,
                "proxies": {
                    target: {
                        "http": asdict(proxy.http),
                        "https": asdict(proxy.https),
                        "socks5": asdict(proxy.socks5),
                    }
                    for target, proxy in ps.proxies.items()
                },
            }
        codex_settings = {}
        for provider_name in CODEX_PROVIDER_OPTIONS:
            defaults = CODEX_PROVIDER_DEFAULTS[provider_name]
            setting = config.codex.provider_settings.get(
                provider_name,
                CodexProviderSettings(
                    base_url=str(defaults["base_url"]),
                    model=str(defaults["default_model"]),
                    reasoning_effort=str(defaults["default_reasoning_effort"]),
                    thinking_enabled=bool(defaults["default_thinking_enabled"]),
                ),
            )
            codex_settings[provider_name] = {
                "base_url": setting.base_url,
                "token": setting.token,
                "model": setting.model,
                "reasoning_effort": setting.reasoning_effort,
                "thinking_enabled": setting.thinking_enabled,
                "model_reasoning": {
                    model: asdict(reasoning)
                    for model, reasoning in setting.model_reasoning.items()
                },
                "proxies": {
                    target: {
                        "http": asdict(proxy.http),
                        "https": asdict(proxy.https),
                        "socks5": asdict(proxy.socks5),
                    }
                    for target, proxy in setting.proxies.items()
                },
            }

        return {
            "provider": config.provider,
            "claude_launch_target": config.claude_launch_target,
            "auth_tokens": config.auth_tokens,
            "project_path": config.project_path,
            "recent_projects": config.recent_projects[:DEFAULT_RECENT_PROJECTS],
            "vscode_path": config.vscode_path,
            "provider_settings": ps_dict,
            "codex": {
                "provider": config.codex.provider,
                "launch_target": config.codex.launch_target,
                "project_path": config.codex.project_path,
                "recent_projects": config.codex.recent_projects[:DEFAULT_RECENT_PROJECTS],
                "provider_settings": codex_settings,
            },
        }
