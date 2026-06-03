# 路径: C:\Users\oucan\Documents\vscode\claude_code启动器\src\ui\widgets\parameter_group.py
# 作用: 启动参数区域控件
#   - DeepSeek / Kimi / 智谱GML / 千问：base_url 不在主界面显示（在鉴权弹窗编辑），
#     模型下拉框可用。
#   - Kimi：不显示 CLAUDE_CODE_EFFORT_LEVEL，显示 ENABLE_TOOL_SEARCH（下拉框，只有 false）。
#   - 智谱GML：不显示 CLAUDE_CODE_EFFORT_LEVEL，显示 CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC（下拉框，只有 1）。
#   - 千问：不显示 CLAUDE_CODE_EFFORT_LEVEL。
#   - Claude中转：base_url 同样不在主界面显示（从 config 静默读取），
#     模型 & effort 使用下拉框（预设选项列表），与固定 provider 保持一致。
#   - Claude官方接口：所有参数行均禁用。

from __future__ import annotations

from PyQt6.QtCore import Qt, QSignalBlocker
from PyQt6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from src.core.config_manager import AppConfig
from src.core.constants import (
    DEFAULT_PROVIDER,
    PROVIDER_OPTIONS,
    PROVIDER_CLAUDE_RELAY,
    PROVIDER_KIMI,
    PROVIDER_ZHIPU,
    get_provider_preset,
)

# 中转 provider 集合
_RELAY_PROVIDERS = {PROVIDER_CLAUDE_RELAY}


class ParameterGroup(QGroupBox):
    def __init__(self, on_pick_project) -> None:
        super().__init__("启动参数")
        self.on_pick_project = on_pick_project

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(PROVIDER_OPTIONS)

        # base_url 输入框：始终隐藏于主界面（所有 provider 均从 config 读取）
        self.base_url_edit = QLineEdit()
        self.base_url_edit.setVisible(False)

        # 模型字段：下拉框（固定 provider 与中转 provider 均使用下拉框）
        self.model_main = QComboBox()
        self.model_opus = QComboBox()
        self.model_sonnet = QComboBox()
        self.model_haiku = QComboBox()
        self.model_subagent = QComboBox()
        self.effort_level = QComboBox()

        # 模型字段：自由输入框（保留控件但不再显示，保证 collect_config_data 兼容性）
        self.model_main_edit = QLineEdit()
        self.model_opus_edit = QLineEdit()
        self.model_sonnet_edit = QLineEdit()
        self.model_haiku_edit = QLineEdit()
        self.model_subagent_edit = QLineEdit()
        # 隐藏所有 edit 控件（中转 provider 也改为下拉框）
        for edit in (
            self.model_main_edit,
            self.model_opus_edit,
            self.model_sonnet_edit,
            self.model_haiku_edit,
            self.model_subagent_edit,
        ):
            edit.setVisible(False)

        for widget in (
            self.provider_combo,
            self.model_main,
            self.model_opus,
            self.model_sonnet,
            self.model_haiku,
            self.model_subagent,
            self.effort_level,
        ):
            widget.setMinimumHeight(26)
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Kimi 专用：ENABLE_TOOL_SEARCH 下拉框（只有 false 一个选项）
        self.enable_tool_search = QComboBox()
        self.enable_tool_search.setMinimumHeight(26)
        self.enable_tool_search.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # GML5 专用：CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC 下拉框（只有 1 一个选项）
        self.disable_nonessential_traffic = QComboBox()
        self.disable_nonessential_traffic.setMinimumHeight(26)
        self.disable_nonessential_traffic.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # GML5 专用：API_TIMEOUT_MS 文本输入框
        self.api_timeout_ms = QLineEdit()
        self.api_timeout_ms.setMinimumHeight(26)
        self.api_timeout_ms.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.project_path_edit = QLineEdit()
        self.project_path_edit.setMinimumHeight(26)
        self.project_path_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.pick_btn = QPushButton("选择工作目录")
        self.pick_btn.setObjectName("pickProjectButton")
        self.pick_btn.setMinimumHeight(26)
        self.pick_btn.setMinimumWidth(120)
        self.pick_btn.clicked.connect(self.on_pick_project)

        self._build_ui()
        self.set_provider(self.provider_combo.currentText())

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._layout = QGridLayout()
        self._layout.setHorizontalSpacing(10)
        self._layout.setVerticalSpacing(10)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setColumnStretch(1, 1)

        # 行 0：Provider
        self._layout.addWidget(self._make_label("Provider"), 0, 0)
        self._layout.addWidget(self.provider_combo, 0, 1)

        # 行 1：ANTHROPIC_MODEL（下拉框）
        self._label_model_main = self._make_label("ANTHROPIC_MODEL")
        self._layout.addWidget(self._label_model_main, 1, 0)
        self._layout.addWidget(self.model_main, 1, 1)

        # 行 2：ANTHROPIC_DEFAULT_OPUS_MODEL
        self._label_model_opus = self._make_label("ANTHROPIC_DEFAULT_OPUS_MODEL")
        self._layout.addWidget(self._label_model_opus, 2, 0)
        self._layout.addWidget(self.model_opus, 2, 1)

        # 行 3：ANTHROPIC_DEFAULT_SONNET_MODEL
        self._label_model_sonnet = self._make_label("ANTHROPIC_DEFAULT_SONNET_MODEL")
        self._layout.addWidget(self._label_model_sonnet, 3, 0)
        self._layout.addWidget(self.model_sonnet, 3, 1)

        # 行 4：ANTHROPIC_DEFAULT_HAIKU_MODEL
        self._label_model_haiku = self._make_label("ANTHROPIC_DEFAULT_HAIKU_MODEL")
        self._layout.addWidget(self._label_model_haiku, 4, 0)
        self._layout.addWidget(self.model_haiku, 4, 1)

        # 行 5：CLAUDE_CODE_SUBAGENT_MODEL
        self._label_model_subagent = self._make_label("CLAUDE_CODE_SUBAGENT_MODEL")
        self._layout.addWidget(self._label_model_subagent, 5, 0)
        self._layout.addWidget(self.model_subagent, 5, 1)

        # 行 6：CLAUDE_CODE_EFFORT_LEVEL
        self._label_effort = self._make_label("CLAUDE_CODE_EFFORT_LEVEL")
        self._layout.addWidget(self._label_effort, 6, 0)
        self._layout.addWidget(self.effort_level, 6, 1)

        # 行 7：ENABLE_TOOL_SEARCH（Kimi 专用）
        self._label_enable_tool_search = self._make_label("ENABLE_TOOL_SEARCH")
        self._layout.addWidget(self._label_enable_tool_search, 7, 0)
        self._layout.addWidget(self.enable_tool_search, 7, 1)

        # 行 8：CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC（GML5 专用）
        self._label_disable_nonessential_traffic = self._make_label("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC")
        self._layout.addWidget(self._label_disable_nonessential_traffic, 8, 0)
        self._layout.addWidget(self.disable_nonessential_traffic, 8, 1)

        # 行 9：API_TIMEOUT_MS（GML5 专用）
        self._label_api_timeout_ms = self._make_label("API_TIMEOUT_MS")
        self._layout.addWidget(self._label_api_timeout_ms, 9, 0)
        self._layout.addWidget(self.api_timeout_ms, 9, 1)

        # 行 10：工作目录
        self._layout.addWidget(self.pick_btn, 10, 0)
        self._layout.addWidget(self.project_path_edit, 10, 1)

        self.setLayout(self._layout)

    @staticmethod
    def _make_label(text: str) -> QLabel:
        label = QLabel(text)
        return label

    # ------------------------------------------------------------------

    def _set_combo_items(self, combo: QComboBox, items: tuple[str, ...], default_text: str) -> None:
        blocker = QSignalBlocker(combo)
        combo.clear()
        if items:
            combo.addItems(list(items))
            if default_text and default_text in items:
                combo.setCurrentText(default_text)
            else:
                combo.setCurrentIndex(0)
        del blocker

    def _hide_all_model_rows(self) -> None:
        """隐藏所有模型行（Claude官方接口）。"""
        for w in (
            self._label_model_main, self.model_main,
            self._label_model_opus, self.model_opus,
            self._label_model_sonnet, self.model_sonnet,
            self._label_model_haiku, self.model_haiku,
            self._label_model_subagent, self.model_subagent,
            self._label_effort, self.effort_level,
            self._label_enable_tool_search, self.enable_tool_search,
            self._label_disable_nonessential_traffic, self.disable_nonessential_traffic,
            self._label_api_timeout_ms, self.api_timeout_ms,
        ):
            w.setVisible(False)

    def _show_all_model_rows(self) -> None:
        """显示所有模型行标签及控件。"""
        for w in (
            self._label_model_main, self.model_main,
            self._label_model_opus, self.model_opus,
            self._label_model_sonnet, self.model_sonnet,
            self._label_model_haiku, self.model_haiku,
            self._label_model_subagent, self.model_subagent,
            self._label_effort, self.effort_level,
            self._label_enable_tool_search, self.enable_tool_search,
            self._label_disable_nonessential_traffic, self.disable_nonessential_traffic,
            self._label_api_timeout_ms, self.api_timeout_ms,
        ):
            w.setVisible(True)

    def set_provider(self, provider: str) -> None:
        preset = get_provider_preset(provider)

        # base_url 输入框始终不在主界面显示
        self.base_url_edit.setVisible(False)
        blocker = QSignalBlocker(self.base_url_edit)
        self.base_url_edit.setText(preset.base_url)
        del blocker

        if not preset.parameters_enabled:
            # Claude官方接口：隐藏所有模型行
            self._hide_all_model_rows()
            return

        # 所有有参数的 provider（含中转）：先全部显示
        self._show_all_model_rows()

        for combo in (
            self.model_main, self.model_opus, self.model_sonnet,
            self.model_haiku, self.model_subagent, self.effort_level,
        ):
            combo.setEnabled(True)

        self._set_combo_items(self.model_main, preset.model_options, preset.anthropic_model_default)
        self._set_combo_items(self.model_opus, preset.model_options, preset.default_opus_model_default)
        self._set_combo_items(self.model_sonnet, preset.model_options, preset.default_sonnet_model_default)
        self._set_combo_items(self.model_haiku, preset.model_options, preset.default_haiku_model_default)
        self._set_combo_items(self.model_subagent, preset.model_options, preset.subagent_model_default)
        self._set_combo_items(self.effort_level, preset.effort_level_options, preset.effort_level_default)

        # 根据预设隐藏/显示 effort_level
        if preset.hide_effort_level:
            self._label_effort.setVisible(False)
            self.effort_level.setVisible(False)
        else:
            self._label_effort.setVisible(True)
            self.effort_level.setVisible(True)

        # 根据预设隐藏/显示 ENABLE_TOOL_SEARCH（Kimi 专用，下拉框）
        if preset.show_enable_tool_search:
            self._label_enable_tool_search.setVisible(True)
            self.enable_tool_search.setVisible(True)
            self._set_combo_items(self.enable_tool_search, preset.enable_tool_search_options, preset.enable_tool_search_default)
        else:
            self._label_enable_tool_search.setVisible(False)
            self.enable_tool_search.setVisible(False)

        # 根据预设隐藏/显示 CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC（GML5 专用，下拉框）
        if preset.show_disable_nonessential_traffic:
            self._label_disable_nonessential_traffic.setVisible(True)
            self.disable_nonessential_traffic.setVisible(True)
            self._set_combo_items(self.disable_nonessential_traffic, preset.disable_nonessential_traffic_options, preset.disable_nonessential_traffic_default)
        else:
            self._label_disable_nonessential_traffic.setVisible(False)
            self.disable_nonessential_traffic.setVisible(False)

        # 根据预设隐藏/显示 API_TIMEOUT_MS（GML5 专用，文本输入框）
        if preset.show_api_timeout_ms:
            self._label_api_timeout_ms.setVisible(True)
            self.api_timeout_ms.setVisible(True)
        else:
            self._label_api_timeout_ms.setVisible(False)
            self.api_timeout_ms.setVisible(False)

    def apply_config(self, config: AppConfig) -> None:
        provider = config.provider if config.provider in PROVIDER_OPTIONS else DEFAULT_PROVIDER

        blocker = QSignalBlocker(self.provider_combo)
        idx = self.provider_combo.findText(provider)
        self.provider_combo.setCurrentIndex(idx if idx >= 0 else 0)
        del blocker

        self.set_provider(provider)

        preset = get_provider_preset(provider)

        # base_url 始终静默写入（不在主界面显示，但 collect_config_data 会读取）
        b = QSignalBlocker(self.base_url_edit)
        self.base_url_edit.setText(config.base_url.strip() or preset.base_url)
        del b

        if not preset.parameters_enabled:
            self.project_path_edit.setText(config.project_path)
            return

        # 所有有参数的 provider（含中转）：下拉框恢复上次选择
        def _restore_combo(combo: QComboBox, config_val: str, preset_default: str) -> None:
            val = config_val.strip() or preset_default
            if combo.findText(val) >= 0:
                combo.setCurrentText(val)
            elif combo.count() > 0:
                combo.setCurrentIndex(0)

        _restore_combo(self.model_main, config.anthropic_model, preset.anthropic_model_default)
        _restore_combo(self.model_opus, config.default_opus_model, preset.default_opus_model_default)
        _restore_combo(self.model_sonnet, config.default_sonnet_model, preset.default_sonnet_model_default)
        _restore_combo(self.model_haiku, config.default_haiku_model, preset.default_haiku_model_default)
        _restore_combo(self.model_subagent, config.subagent_model, preset.subagent_model_default)

        effort = config.effort_level.strip() or preset.effort_level_default
        if self.effort_level.findText(effort) >= 0:
            self.effort_level.setCurrentText(effort)

        # Kimi 专用参数恢复
        if preset.show_enable_tool_search:
            val = config.enable_tool_search.strip() or preset.enable_tool_search_default
            if self.enable_tool_search.findText(val) >= 0:
                self.enable_tool_search.setCurrentText(val)
            elif self.enable_tool_search.count() > 0:
                self.enable_tool_search.setCurrentIndex(0)

        # GML5 专用参数恢复
        if preset.show_disable_nonessential_traffic:
            val = config.disable_nonessential_traffic.strip() or preset.disable_nonessential_traffic_default
            if self.disable_nonessential_traffic.findText(val) >= 0:
                self.disable_nonessential_traffic.setCurrentText(val)
            elif self.disable_nonessential_traffic.count() > 0:
                self.disable_nonessential_traffic.setCurrentIndex(0)

        # GML5 专用：API_TIMEOUT_MS 恢复
        if preset.show_api_timeout_ms:
            val = config.api_timeout_ms.strip() or preset.api_timeout_ms_default
            self.api_timeout_ms.setText(val)

        self.project_path_edit.setText(config.project_path)

    def collect_config_data(self) -> dict:
        """收集当前 UI 上的参数配置，统一从下拉框读取。"""
        provider = self.provider_combo.currentText()
        preset = get_provider_preset(provider)
        return {
            "provider": provider,
            "base_url": self.base_url_edit.text().strip(),
            "anthropic_model": self.model_main.currentText(),
            "default_opus_model": self.model_opus.currentText(),
            "default_sonnet_model": self.model_sonnet.currentText(),
            "default_haiku_model": self.model_haiku.currentText(),
            "subagent_model": self.model_subagent.currentText(),
            "effort_level": self.effort_level.currentText(),
            "project_path": self.project_path_edit.text().strip(),
            "enable_tool_search": self.enable_tool_search.currentText() if preset.show_enable_tool_search else "",
            "disable_nonessential_traffic": self.disable_nonessential_traffic.currentText() if preset.show_disable_nonessential_traffic else "",
            "api_timeout_ms": self.api_timeout_ms.text().strip() if preset.show_api_timeout_ms else "",
        }

    def set_project_path(self, path: str) -> None:
        self.project_path_edit.setText(path)
