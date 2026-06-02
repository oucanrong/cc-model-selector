# 路径: src/services/env_builder_service.py
# 作用: 构建 Claude Code 启动环境变量

from __future__ import annotations

import os

from src.core.config_manager import AppConfig
from src.core.constants import (
    PROVIDER_CLAUDE_DEFAULT,
    PROVIDER_CLAUDE_RELAY,
    PROVIDER_GPT_RELAY,
    get_provider_preset,
)
from .proxy_service import build_proxy_env

# Claude官方接口需要清理的环境变量前缀（除代理和 PYTHONUTF8 外的所有注入变量）
_CLAUDE_DEFAULT_CLEANUP_KEYS = [
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "CLAUDE_CODE_SUBAGENT_MODEL",
    "CLAUDE_CODE_EFFORT_LEVEL",
    "ENABLE_TOOL_SEARCH",
    "API_TIMEOUT_MS",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
]


def build_env(config: AppConfig) -> dict[str, str]:
    env = os.environ.copy()
    preset = get_provider_preset(config.provider)

    token = config.token.strip()

    if config.provider == PROVIDER_CLAUDE_DEFAULT:
        # Claude官方接口：不注入任何鉴权/API环境变量，
        # 主动清理可能从 os.environ 残留的变量，相当于在终端上直接执行 claude 命令。
        for key in _CLAUDE_DEFAULT_CLEANUP_KEYS:
            env.pop(key, None)

    else:
        # 所有第三方 Provider（DeepSeek / Kimi / 智谱GML / Claude中转 / GPT中转）：
        # 注入 token，并清除 ANTHROPIC_API_KEY。
        # 原因：Claude Code 会优先读取 ANTHROPIC_API_KEY；若该变量存在但为空，
        # 即使 ANTHROPIC_AUTH_TOKEN 已正确设置，Claude Code 也会报"未登录"。
        env.pop("ANTHROPIC_API_KEY", None)
        if token:
            env["ANTHROPIC_AUTH_TOKEN"] = token
        else:
            env.pop("ANTHROPIC_AUTH_TOKEN", None)

        if preset.parameters_enabled:
            # base_url：优先使用 config 中保存的值（含用户在鉴权弹窗中编辑的中转地址），
            # 回退到预设默认值。
            base_url = config.base_url.strip() or preset.base_url
            if base_url:
                env["ANTHROPIC_BASE_URL"] = base_url
            else:
                env.pop("ANTHROPIC_BASE_URL", None)

            # 模型参数：中转 provider 用用户输入值（可为空，为空则不注入）；
            # 固定 provider 回退到预设默认值。
            is_relay = config.provider in (PROVIDER_CLAUDE_RELAY, PROVIDER_GPT_RELAY)

            def _model_val(config_val: str, preset_default: str) -> str:
                v = config_val.strip()
                if v:
                    return v
                return "" if is_relay else preset_default

            model_main = _model_val(config.anthropic_model, preset.anthropic_model_default)
            model_opus = _model_val(config.default_opus_model, preset.default_opus_model_default)
            model_sonnet = _model_val(config.default_sonnet_model, preset.default_sonnet_model_default)
            model_haiku = _model_val(config.default_haiku_model, preset.default_haiku_model_default)
            subagent = _model_val(config.subagent_model, preset.subagent_model_default)

            if model_main:
                env["ANTHROPIC_MODEL"] = model_main
            if model_opus:
                env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = model_opus
            if model_sonnet:
                env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = model_sonnet
            if model_haiku:
                env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = model_haiku
            if subagent:
                env["CLAUDE_CODE_SUBAGENT_MODEL"] = subagent

            # CLAUDE_CODE_EFFORT_LEVEL：仅对非 Kimi、非 GML5 的 provider 注入
            if preset.hide_effort_level:
                # Kimi / GML5 不使用此参数，确保环境变量中不存在
                env.pop("CLAUDE_CODE_EFFORT_LEVEL", None)
            else:
                effort = config.effort_level.strip() or (preset.effort_level_default if not is_relay else "")
                if effort:
                    env["CLAUDE_CODE_EFFORT_LEVEL"] = effort

            # Kimi 专用：ENABLE_TOOL_SEARCH
            if preset.show_enable_tool_search:
                val = config.enable_tool_search.strip() or preset.enable_tool_search_default
                if val:
                    env["ENABLE_TOOL_SEARCH"] = val

            # GML5 专用：CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC
            if preset.show_disable_nonessential_traffic:
                val = config.disable_nonessential_traffic.strip() or preset.disable_nonessential_traffic_default
                if val:
                    env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = val

            # GML5 专用：API_TIMEOUT_MS
            if preset.show_api_timeout_ms:
                val = config.api_timeout_ms.strip() or preset.api_timeout_ms_default
                if val:
                    env["API_TIMEOUT_MS"] = val

    env["PYTHONUTF8"] = "1"
    env.update(build_proxy_env(config.proxy))
    return env
