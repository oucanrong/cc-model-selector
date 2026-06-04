# 路径: C:\Users\oucan\Documents\vscode\claude_code启动器\src\core\constants.py
# 作用: 全局常量与 Provider 预设

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

APP_NAME = "Claude-Code模型管理器v1.6"

ROOT_DIR = Path(__file__).resolve().parents[2]
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
PROVIDER_ZHIPU = "智谱GML"
PROVIDER_QWEN = "阿里千问"
PROVIDER_MINIMAX = "MINIMAX"
PROVIDER_CLAUDE_RELAY = "Claude中转"

PROVIDER_OPTIONS = [
    PROVIDER_CLAUDE_DEFAULT,
    PROVIDER_DEEPSEEK,
    PROVIDER_KIMI,
    PROVIDER_ZHIPU,
    PROVIDER_QWEN,
    PROVIDER_MINIMAX,
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
    # GML5 / MINIMAX 专用：是否显示 CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC 参数
    show_disable_nonessential_traffic: bool = False
    # GML5 / MINIMAX 专用：CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC 下拉框选项
    disable_nonessential_traffic_options: tuple[str, ...] = ("1",)
    disable_nonessential_traffic_default: str = "1"
    # GML5 / MINIMAX 专用：是否显示 API_TIMEOUT_MS 参数
    show_api_timeout_ms: bool = False
    # GML5 / MINIMAX 专用：API_TIMEOUT_MS 默认值
    api_timeout_ms_default: str = "3000000"
    # 是否隐藏 CLAUDE_CODE_EFFORT_LEVEL（Kimi / GML5 / 阿里千问 / MINIMAX 不再显示该参数）
    hide_effort_level: bool = False


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
