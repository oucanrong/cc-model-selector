# 路径: C:\Users\oucan\Documents\vscode\claude_code启动器\src\core\constants.py
# 作用: 全局常量与 Provider 预设

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

APP_NAME = "cc模型管理器v2.2"


def application_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


ROOT_DIR = application_root()
CONFIG_PATH = ROOT_DIR / "config.json"
LOG_DIR = ROOT_DIR / "logs"
LOG_FILE = LOG_DIR / "app.log"

DEFAULT_PROVIDER = "Claude官方接口"
DEFAULT_BASE_URL = ""
DEFAULT_MODEL = ""
DEFAULT_OPUS_MODEL = ""
DEFAULT_SONNET_MODEL = ""
DEFAULT_HAIKU_MODEL = ""
DEFAULT_SUBAGENT_MODEL = ""
DEFAULT_EFFORT_LEVEL = "max"
DEFAULT_MAX_LOG_LINES = 5000
DEFAULT_RECENT_PROJECTS = 10

PROVIDER_CLAUDE_DEFAULT = "Claude官方接口"
PROVIDER_DEEPSEEK = "DeepSeek"
PROVIDER_KIMI = "Kimi"
PROVIDER_ZHIPU = "智谱GLM"
PROVIDER_QWEN = "阿里千问"
PROVIDER_MINIMAX = "MiniMax"
PROVIDER_XIAOMI_MIMO = "小米MiMo"
PROVIDER_ARK_CODING = "方舟Coding Plan"
PROVIDER_CLAUDE_RELAY = "Claude中转"

CODEX_PROVIDER_OFFICIAL = "Codex官方接口"
CODEX_PROVIDER_DEEPSEEK = "DeepSeek"
CODEX_PROVIDER_KIMI = "Kimi"
CODEX_PROVIDER_ZHIPU = "智谱GLM"
CODEX_PROVIDER_QWEN = "阿里千问"
CODEX_PROVIDER_MINIMAX = "MiniMax"
CODEX_PROVIDER_XIAOMI_MIMO = "小米MiMo"
CODEX_PROVIDER_ARK_CODING = "方舟Coding Plan"
CODEX_PROVIDER_GPT_RELAY = "GPT中转"

CODEX_PROTOCOL_OFFICIAL = "official"
CODEX_PROTOCOL_CHAT_PROXY = "chat_proxy"
CODEX_PROTOCOL_RESPONSES_DIRECT = "responses_direct"
CODEX_API_KEY_ENV = "CC_MODEL_MANAGER_CODEX_API_KEY"
CODEX_REASONING_CONTROL_NONE = "none"
CODEX_REASONING_CONTROL_EFFORT = "effort"
CODEX_REASONING_CONTROL_TOGGLE = "toggle"

CLAUDE_LAUNCH_TARGET_DEFAULT = "cli"
CLAUDE_LAUNCH_TARGET_OPTIONS = (
    ("cli", "启动Claude Code cli版"),
    ("vscode", "启动VS Code"),
    ("upgrade", "升级Claude Code cli版"),
)
CODEX_LAUNCH_TARGET_DEFAULT = "desktop"
CODEX_LAUNCH_TARGET_OPTIONS = (
    ("desktop", "启动Codex 桌面版"),
    ("cli", "启动Codex cli版"),
    ("vscode", "启动VS Code"),
    ("upgrade", "升级Codex cli版"),
)

CODEX_PROVIDER_OPTIONS = [
    CODEX_PROVIDER_OFFICIAL,
    CODEX_PROVIDER_DEEPSEEK,
    CODEX_PROVIDER_KIMI,
    CODEX_PROVIDER_ZHIPU,
    CODEX_PROVIDER_QWEN,
    CODEX_PROVIDER_MINIMAX,
    CODEX_PROVIDER_XIAOMI_MIMO,
    CODEX_PROVIDER_ARK_CODING,
    CODEX_PROVIDER_GPT_RELAY,
]

CODEX_PROVIDER_DEFAULTS = {
    CODEX_PROVIDER_OFFICIAL: {
        "base_url": "",
        "models": (),
        "default_model": "",
        "protocol": CODEX_PROTOCOL_OFFICIAL,
        "reasoning_control": CODEX_REASONING_CONTROL_NONE,
        "reasoning_options": (),
        "default_reasoning_effort": "",
        "default_thinking_enabled": False,
    },
    CODEX_PROVIDER_DEEPSEEK: {
        "base_url": "https://api.deepseek.com",
        "models": ("deepseek-v4-pro", "deepseek-v4-flash"),
        "default_model": "deepseek-v4-pro",
        "display_names": {
            "deepseek-v4-pro": "DeepSeek V4 Pro",
            "deepseek-v4-flash": "DeepSeek V4 Flash",
        },
        "context_window": 1_000_000,
        "protocol": CODEX_PROTOCOL_CHAT_PROXY,
        "reasoning_control": CODEX_REASONING_CONTROL_EFFORT,
        "reasoning_options": ("none", "high", "max"),
        "default_reasoning_effort": "high",
        "default_thinking_enabled": False,
        "chat_reasoning": {
            "thinking_param": "thinking",
            "effort_param": "reasoning_effort",
            "effort_map": {
                "low": "high",
                "medium": "high",
                "xhigh": "max",
            },
            "response_fields": (
                "reasoning_content",
                "reasoning",
                "reasoning_details",
            ),
            "tool_call_reasoning_required": True,
        },
    },
    CODEX_PROVIDER_KIMI: {
        "base_url": "https://api.moonshot.cn/v1",
        "models": ("kimi-k2.6",),
        "default_model": "kimi-k2.6",
        "display_names": {"kimi-k2.6": "Kimi K2.6"},
        "context_window": 256_000,
        "protocol": CODEX_PROTOCOL_CHAT_PROXY,
        "reasoning_control": CODEX_REASONING_CONTROL_TOGGLE,
        "reasoning_options": (),
        "default_reasoning_effort": "",
        "default_thinking_enabled": True,
        "chat_reasoning": {
            "thinking_param": "thinking",
            "effort_param": "",
            "effort_map": {},
            "response_fields": (
                "reasoning_content",
                "reasoning",
                "reasoning_details",
            ),
            "tool_call_reasoning_required": True,
        },
    },
    CODEX_PROVIDER_ZHIPU: {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": ("glm-5.1", "glm-5-turbo", "glm-4.5-air"),
        "default_model": "glm-5.1",
        "display_names": {
            "glm-5.1": "GLM-5.1",
            "glm-5-turbo": "GLM-5 Turbo",
            "glm-4.5-air": "GLM-4.5 Air",
        },
        "context_window": 200_000,
        "protocol": CODEX_PROTOCOL_CHAT_PROXY,
        "reasoning_control": CODEX_REASONING_CONTROL_TOGGLE,
        "reasoning_options": (),
        "default_reasoning_effort": "",
        "default_thinking_enabled": True,
        "chat_reasoning": {
            "thinking_param": "thinking",
            "effort_param": "",
            "effort_map": {},
            "response_fields": (
                "reasoning_content",
                "reasoning",
                "reasoning_details",
            ),
            "tool_call_reasoning_required": True,
        },
    },
    CODEX_PROVIDER_QWEN: {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ("qwen3.6-flash", "qwen3.7-plus", "qwen3.7-max"),
        "default_model": "qwen3.7-max",
        "display_names": {
            "qwen3.6-flash": "Qwen 3.6 Flash",
            "qwen3.7-plus": "Qwen 3.7 Plus",
            "qwen3.7-max": "Qwen 3.7 Max",
        },
        "context_windows": {
            "qwen3.6-flash": 256_000,
            "qwen3.7-plus": 1_000_000,
            "qwen3.7-max": 1_000_000,
        },
        "protocol": CODEX_PROTOCOL_RESPONSES_DIRECT,
        "reasoning_control": CODEX_REASONING_CONTROL_EFFORT,
        "provider_id": "qwen",
        "provider_name": "阿里千问",
        "reasoning_options": ("none", "minimal", "low", "medium", "high"),
        "default_reasoning_effort": "medium",
        "default_thinking_enabled": False,
    },
    CODEX_PROVIDER_MINIMAX: {
        "base_url": "https://api.minimaxi.com/v1",
        "models": ("MiniMax-M3",),
        "default_model": "MiniMax-M3",
        "display_names": {"MiniMax-M3": "MiniMax M3"},
        "context_window": 512_000,
        "protocol": CODEX_PROTOCOL_RESPONSES_DIRECT,
        "reasoning_control": CODEX_REASONING_CONTROL_NONE,
        "provider_id": "minimax",
        "provider_name": "MiniMax",
        "reasoning_options": (),
        "default_reasoning_effort": "",
        "default_thinking_enabled": False,
    },
    CODEX_PROVIDER_XIAOMI_MIMO: {
        "base_url": "https://api.xiaomimimo.com/v1",
        "models": ("mimo-v2.5", "mimo-v2.5-pro"),
        "default_model": "mimo-v2.5-pro",
        "display_names": {
            "mimo-v2.5": "MiMo V2.5",
            "mimo-v2.5-pro": "MiMo V2.5 Pro",
        },
        "context_window": 1_000_000,
        "protocol": CODEX_PROTOCOL_CHAT_PROXY,
        "reasoning_control": CODEX_REASONING_CONTROL_TOGGLE,
        "reasoning_options": (),
        "default_reasoning_effort": "",
        "default_thinking_enabled": True,
        "chat_reasoning": {
            "thinking_param": "thinking",
            "effort_param": "",
            "effort_map": {},
            "response_fields": (
                "reasoning_content",
                "reasoning",
                "reasoning_details",
            ),
            "tool_call_reasoning_required": False,
        },
    },
    CODEX_PROVIDER_ARK_CODING: {
        "base_url": "https://ark.cn-beijing.volces.com/api/coding/v3",
        "models": (
            "doubao-seed-2.0-code",
            "doubao-seed-2.0-pro",
            "doubao-seed-2.0-lite",
            "minimax-latest",
            "glm-5.1",
            "deepseek-v4-flash",
            "deepseek-v4-pro",
            "kimi-k2.6",
        ),
        "default_model": "doubao-seed-2.0-code",
        "context_window": 256_000,
        "context_windows": {
            "doubao-seed-2.0-code": 256_000,
            "doubao-seed-2.0-pro": 256_000,
            "doubao-seed-2.0-lite": 256_000,
            "minimax-latest": 512_000,
            "glm-5.1": 200_000,
            "deepseek-v4-flash": 1_000_000,
            "deepseek-v4-pro": 1_000_000,
            "kimi-k2.6": 256_000,
        },
        "protocol": CODEX_PROTOCOL_CHAT_PROXY,
        "reasoning_control": CODEX_REASONING_CONTROL_NONE,
        "reasoning_options": (),
        "default_reasoning_effort": "",
        "default_thinking_enabled": False,
        "chat_reasoning": {
            "thinking_param": "thinking",
            "effort_param": "",
            "effort_map": {},
            "response_fields": (
                "reasoning_content",
                "reasoning",
                "reasoning_details",
            ),
            "tool_call_reasoning_required": False,
        },
    },
    CODEX_PROVIDER_GPT_RELAY: {
        "base_url": "",
        "models": ("gpt-5.5",),
        "default_model": "gpt-5.5",
        "display_names": {"gpt-5.5": "GPT-5.5"},
        "protocol": CODEX_PROTOCOL_RESPONSES_DIRECT,
        "reasoning_control": CODEX_REASONING_CONTROL_EFFORT,
        "provider_id": "gpt_relay",
        "provider_name": "GPT中转",
        "reasoning_options": ("minimal", "low", "medium", "high", "xhigh"),
        "default_reasoning_effort": "medium",
        "default_thinking_enabled": False,
    },
}


def get_codex_context_window(provider: str, model: str) -> int | None:
    defaults = CODEX_PROVIDER_DEFAULTS[provider]
    context_windows = defaults.get("context_windows")
    if isinstance(context_windows, dict):
        value = context_windows.get(model)
        return int(value) if value is not None else None
    value = defaults.get("context_window")
    return int(value) if value is not None else None

PROVIDER_OPTIONS = [
    PROVIDER_CLAUDE_DEFAULT,
    PROVIDER_DEEPSEEK,
    PROVIDER_KIMI,
    PROVIDER_ZHIPU,
    PROVIDER_QWEN,
    PROVIDER_MINIMAX,
    PROVIDER_XIAOMI_MIMO,
    PROVIDER_ARK_CODING,
    PROVIDER_CLAUDE_RELAY,
]


@dataclass(frozen=True)
class ProviderPreset:
    base_url: str
    model_options: tuple[str, ...]
    anthropic_model_default: str
    default_opus_model_default: str
    default_sonnet_model_default: str
    default_haiku_model_default: str
    subagent_model_default: str
    effort_level_options: tuple[str, ...]
    effort_level_default: str
    parameters_enabled: bool
    base_url_editable: bool = False
    show_base_url_in_main: bool = False
    # Kimi 专用：是否显示 ENABLE_TOOL_SEARCH 参数
    show_enable_tool_search: bool = False
    # Kimi 专用：ENABLE_TOOL_SEARCH 下拉框选项
    enable_tool_search_options: tuple[str, ...] = ("false",)
    enable_tool_search_default: str = "false"
    # GLM5 / MINIMAX 专用：是否显示 CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC 参数
    show_disable_nonessential_traffic: bool = False
    # GLM5 / MINIMAX 专用：CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC 下拉框选项
    disable_nonessential_traffic_options: tuple[str, ...] = ("1",)
    disable_nonessential_traffic_default: str = "1"
    # GLM5 / MINIMAX 专用：是否显示 API_TIMEOUT_MS 参数
    show_api_timeout_ms: bool = False
    # GLM5 / MINIMAX 专用：API_TIMEOUT_MS 默认值
    api_timeout_ms_default: str = "3000000"
    # 是否隐藏 CLAUDE_CODE_EFFORT_LEVEL（Kimi / GLM5 / 阿里千问 / MINIMAX 不再显示该参数）
    hide_effort_level: bool = False
    # 小米MiMo / 方舟Coding Plan 专用：是否显示 hasCompletedOnboarding 参数
    show_has_completed_onboarding: bool = False
    # 小米MiMo / 方舟Coding Plan 专用：hasCompletedOnboarding 下拉框选项
    has_completed_onboarding_options: tuple[str, ...] = ("true",)
    has_completed_onboarding_default: str = "true"


PROVIDER_PRESETS: dict[str, ProviderPreset] = {
    PROVIDER_CLAUDE_DEFAULT: ProviderPreset(
        base_url="",
        model_options=(),
        anthropic_model_default="",
        default_opus_model_default="",
        default_sonnet_model_default="",
        default_haiku_model_default="",
        subagent_model_default="",
        effort_level_options=(),
        effort_level_default="",
        parameters_enabled=False,
        base_url_editable=False,
        show_base_url_in_main=False,
    ),
    PROVIDER_DEEPSEEK: ProviderPreset(
        base_url="https://api.deepseek.com/anthropic",
        model_options=("deepseek-v4-flash", "deepseek-v4-pro[1m]"),
        anthropic_model_default="deepseek-v4-pro[1m]",
        default_opus_model_default="deepseek-v4-pro[1m]",
        default_sonnet_model_default="deepseek-v4-pro[1m]",
        default_haiku_model_default="deepseek-v4-flash",
        subagent_model_default="deepseek-v4-pro[1m]",
        effort_level_options=("max",),
        effort_level_default="max",
        parameters_enabled=True,
        base_url_editable=True,
        show_base_url_in_main=False,
    ),
    PROVIDER_KIMI: ProviderPreset(
        base_url="https://api.moonshot.cn/anthropic",
        model_options=("kimi-k2.6",),
        anthropic_model_default="kimi-k2.6",
        default_opus_model_default="kimi-k2.6",
        default_sonnet_model_default="kimi-k2.6",
        default_haiku_model_default="kimi-k2.6",
        subagent_model_default="kimi-k2.6",
        effort_level_options=("max",),
        effort_level_default="max",
        parameters_enabled=True,
        base_url_editable=True,
        show_base_url_in_main=False,
        show_enable_tool_search=True,
        enable_tool_search_options=("false",),
        enable_tool_search_default="false",
        hide_effort_level=True,
    ),
    PROVIDER_ZHIPU: ProviderPreset(
        base_url="https://open.bigmodel.cn/api/anthropic",
        model_options=("glm-4.5-air", "glm-5-turbo", "glm-5.1"),
        anthropic_model_default="glm-5.1",
        default_opus_model_default="glm-5.1",
        default_sonnet_model_default="glm-5-turbo",
        default_haiku_model_default="glm-4.5-air",
        subagent_model_default="glm-5-turbo",
        effort_level_options=("max",),
        effort_level_default="max",
        parameters_enabled=True,
        base_url_editable=True,
        show_base_url_in_main=False,
        show_disable_nonessential_traffic=True,
        disable_nonessential_traffic_options=("1",),
        disable_nonessential_traffic_default="1",
        show_api_timeout_ms=True,
        api_timeout_ms_default="3000000",
        hide_effort_level=True,
    ),
    PROVIDER_QWEN: ProviderPreset(
        base_url="https://dashscope.aliyuncs.com/apps/anthropic",
        model_options=("qwen3.7-max", "qwen3.7-plus", "qwen3.6-flash"),
        anthropic_model_default="qwen3.7-max",
        default_opus_model_default="qwen3.7-max",
        default_sonnet_model_default="qwen3.7-max",
        default_haiku_model_default="qwen3.6-flash",
        subagent_model_default="qwen3.7-max",
        effort_level_options=("max",),
        effort_level_default="max",
        parameters_enabled=True,
        base_url_editable=True,
        show_base_url_in_main=False,
        hide_effort_level=True,
    ),
    PROVIDER_MINIMAX: ProviderPreset(
        base_url="https://api.minimaxi.com/anthropic",
        model_options=("MiniMax-M3",),
        anthropic_model_default="MiniMax-M3",
        default_opus_model_default="MiniMax-M3",
        default_sonnet_model_default="MiniMax-M3",
        default_haiku_model_default="MiniMax-M3",
        subagent_model_default="MiniMax-M3",
        effort_level_options=("max",),
        effort_level_default="max",
        parameters_enabled=True,
        base_url_editable=True,
        show_base_url_in_main=False,
        show_disable_nonessential_traffic=True,
        disable_nonessential_traffic_options=("1",),
        disable_nonessential_traffic_default="1",
        show_api_timeout_ms=True,
        api_timeout_ms_default="3000000",
        hide_effort_level=True,
    ),
    PROVIDER_XIAOMI_MIMO: ProviderPreset(
        base_url="https://api.xiaomimimo.com/anthropic",
        model_options=("mimo-v2.5", "mimo-v2.5-pro"),
        anthropic_model_default="mimo-v2.5-pro",
        default_opus_model_default="mimo-v2.5-pro",
        default_sonnet_model_default="mimo-v2.5-pro",
        default_haiku_model_default="mimo-v2.5",
        subagent_model_default="mimo-v2.5-pro",
        effort_level_options=("max",),
        effort_level_default="max",
        parameters_enabled=True,
        base_url_editable=True,
        show_base_url_in_main=False,
        hide_effort_level=True,
        show_has_completed_onboarding=True,
        has_completed_onboarding_options=("true",),
        has_completed_onboarding_default="true",
    ),
    PROVIDER_ARK_CODING: ProviderPreset(
        base_url="https://ark.cn-beijing.volces.com/api/coding",
        model_options=(
            "doubao-seed-2.0-code",
            "doubao-seed-2.0-pro",
            "doubao-seed-2.0-lite",
            "minimax-latest",
            "glm-5.1",
            "deepseek-v4-flash",
            "deepseek-v4-pro",
            "kimi-k2.6",
        ),
        anthropic_model_default="doubao-seed-2.0-code",
        default_opus_model_default="doubao-seed-2.0-code",
        default_sonnet_model_default="doubao-seed-2.0-code",
        default_haiku_model_default="doubao-seed-2.0-code",
        subagent_model_default="doubao-seed-2.0-code",
        effort_level_options=("max",),
        effort_level_default="max",
        parameters_enabled=True,
        base_url_editable=True,
        show_base_url_in_main=False,
        hide_effort_level=True,
        show_has_completed_onboarding=True,
        has_completed_onboarding_options=("true",),
        has_completed_onboarding_default="true",
    ),
    PROVIDER_CLAUDE_RELAY: ProviderPreset(
        base_url="",
        model_options=("claude-sonnet-4-6", "claude-opus-4-8", "claude-haiku-4-5-20251001"),
        anthropic_model_default="claude-sonnet-4-6",
        default_opus_model_default="claude-opus-4-8",
        default_sonnet_model_default="claude-sonnet-4-6",
        default_haiku_model_default="claude-haiku-4-5-20251001",
        subagent_model_default="claude-sonnet-4-6",
        effort_level_options=("low", "medium", "high", "max"),
        effort_level_default="high",
        parameters_enabled=True,
        base_url_editable=True,
        show_base_url_in_main=False,
    ),
}


def get_provider_preset(provider: str) -> ProviderPreset:
    return PROVIDER_PRESETS.get(provider, PROVIDER_PRESETS[DEFAULT_PROVIDER])
