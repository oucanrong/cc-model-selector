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


def build_env(config: AppConfig) -> dict[str, str]:
    env = os.environ.copy()
    preset = get_provider_preset(config.provider)

    token = config.token.strip()

    if config.provider == PROVIDER_CLAUDE_DEFAULT:
        # Claude官方接口：不注入任何鉴权/API环境变量，由 Claude Code 自身管理登录态
        env.pop("ANTHROPIC_AUTH_TOKEN", None)
        env.pop("ANTHROPIC_API_KEY", None)

    elif config.provider in (PROVIDER_CLAUDE_RELAY, PROVIDER_GPT_RELAY):
        # 中转 Provider：注入 token + 用户自填的 base_url；清除 ANTHROPIC_API_KEY
        env.pop("ANTHROPIC_API_KEY", None)
        if token:
            env["ANTHROPIC_AUTH_TOKEN"] = token
        else:
            env.pop("ANTHROPIC_AUTH_TOKEN", None)

        base_url = config.base_url.strip()
        if base_url:
            env["ANTHROPIC_BASE_URL"] = base_url
        else:
            env.pop("ANTHROPIC_BASE_URL", None)

    else:
        # 第三方固定 Provider（DeepSeek / Kimi / 智谱GML）：
        # 必须注入 token，并同时清除 ANTHROPIC_API_KEY。
        # 原因：Claude Code 会优先读取 ANTHROPIC_API_KEY；若该变量存在但为空，
        # 即使 ANTHROPIC_AUTH_TOKEN 已正确设置，Claude Code 也会报"未登录"。
        env.pop("ANTHROPIC_API_KEY", None)
        if token:
            env["ANTHROPIC_AUTH_TOKEN"] = token
        else:
            env.pop("ANTHROPIC_AUTH_TOKEN", None)

    if preset.parameters_enabled:
        env["ANTHROPIC_BASE_URL"] = config.base_url.strip() or preset.base_url
        env["ANTHROPIC_MODEL"] = config.anthropic_model.strip() or preset.anthropic_model_default
        env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = (
            config.default_opus_model.strip() or preset.default_opus_model_default
        )
        env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = (
            config.default_sonnet_model.strip() or preset.default_sonnet_model_default
        )
        env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = (
            config.default_haiku_model.strip() or preset.default_haiku_model_default
        )
        env["CLAUDE_CODE_SUBAGENT_MODEL"] = (
            config.subagent_model.strip() or preset.subagent_model_default
        )
        env["CLAUDE_CODE_EFFORT_LEVEL"] = config.effort_level.strip() or preset.effort_level_default

    env["PYTHONUTF8"] = "1"
    env.update(build_proxy_env(config.proxy))
    return env
