# 路径: src/core/constants.py
# 作用: 全局常量与 Provider 预设

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

APP_NAME = "Claude-Code模型选择器"

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
PROVIDER_CLAUDE_RELAY = "Claude中转"
PROVIDER_GPT_RELAY = "GPT中转"

PROVIDER_OPTIONS = [
    PROVIDER_CLAUDE_DEFAULT,
    PROVIDER_DEEPSEEK,
    PROVIDER_KIMI,
    PROVIDER_ZHIPU,
    PROVIDER_CLAUDE_RELAY,
    PROVIDER_GPT_RELAY,
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
    # base_url 是否在鉴权弹窗中可编辑（DeepSeek/Kimi/GML/中转均可编辑）
    base_url_editable: bool = False
    # base_url 是否在主界面中显示（仅中转 provider 不在主界面显示，从 config 静默读取）
    show_base_url_in_main: bool = False


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
        subagent_model_default="deepseek-v4-flash",
        effort_level_options=("max",),
        effort_level_default="max",
        parameters_enabled=True,
        base_url_editable=True,
        show_base_url_in_main=False,
    ),
    PROVIDER_KIMI: ProviderPreset(
        base_url="https://api.moonshot.cn/anthropic",
        model_options=("kimi-k2.5",),
        anthropic_model_default="kimi-k2.5",
        default_opus_model_default="kimi-k2.5",
        default_sonnet_model_default="kimi-k2.5",
        default_haiku_model_default="kimi-k2.5",
        subagent_model_default="kimi-k2.5",
        effort_level_options=("max",),
        effort_level_default="max",
        parameters_enabled=True,
        base_url_editable=True,
        show_base_url_in_main=False,
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
    ),
    PROVIDER_CLAUDE_RELAY: ProviderPreset(
        base_url="",
        # 中转不预设模型列表，用户自由输入；使用空 tuple 触发可编辑 QLineEdit 模式
        model_options=(),
        anthropic_model_default="",
        default_opus_model_default="",
        default_sonnet_model_default="",
        default_haiku_model_default="",
        subagent_model_default="",
        effort_level_options=("low", "medium", "high", "max"),
        effort_level_default="max",
        parameters_enabled=True,
        base_url_editable=True,
        show_base_url_in_main=False,
    ),
    PROVIDER_GPT_RELAY: ProviderPreset(
        base_url="",
        model_options=(),
        anthropic_model_default="",
        default_opus_model_default="",
        default_sonnet_model_default="",
        default_haiku_model_default="",
        subagent_model_default="",
        effort_level_options=("low", "medium", "high", "max"),
        effort_level_default="max",
        parameters_enabled=True,
        base_url_editable=True,
        show_base_url_in_main=False,
    ),
}


def get_provider_preset(provider: str) -> ProviderPreset:
    return PROVIDER_PRESETS.get(provider, PROVIDER_PRESETS[DEFAULT_PROVIDER])
