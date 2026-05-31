# 路径: src/ui/widgets/parameter_group.py
# 作用: 启动参数区域控件（支持 Claude中转 / GPT中转 可编辑 base_url）

from __future__ import annotations

from PyQt6.QtCore import QSignalBlocker
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
    get_provider_preset,
)


class ParameterGroup(QGroupBox):
    def __init__(self, on_pick_project) -> None:
        super().__init__("启动参数")
        self.on_pick_project = on_pick_project

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(PROVIDER_OPTIONS)

        self.base_url_edit = QLineEdit()
        self.base_url_edit.setVisible(False)
        self.base_url_edit.setPlaceholderText("Base URL（中转地址）")

        self.model_main = QComboBox()
        self.model_opus = QComboBox()
        self.model_sonnet = QComboBox()
        self.model_haiku = QComboBox()
        self.model_subagent = QComboBox()
        self.effort_level = QComboBox()

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

        # 行 1：ANTHROPIC_BASE_URL（中转 provider 可见，其余隐藏）
        self._base_url_label = self._make_label("ANTHROPIC_BASE_URL")
        self._layout.addWidget(self._base_url_label, 1, 0)
        self._layout.addWidget(self.base_url_edit, 1, 1)

        # 行 2~7：模型 & effort（非 Claude官方接口 时启用）
        self._layout.addWidget(self._make_label("ANTHROPIC_MODEL"), 2, 0)
        self._layout.addWidget(self.model_main, 2, 1)

        self._layout.addWidget(self._make_label("ANTHROPIC_DEFAULT_OPUS_MODEL"), 3, 0)
        self._layout.addWidget(self.model_opus, 3, 1)

        self._layout.addWidget(self._make_label("ANTHROPIC_DEFAULT_SONNET_MODEL"), 4, 0)
        self._layout.addWidget(self.model_sonnet, 4, 1)

        self._layout.addWidget(self._make_label("ANTHROPIC_DEFAULT_HAIKU_MODEL"), 5, 0)
        self._layout.addWidget(self.model_haiku, 5, 1)

        self._layout.addWidget(self._make_label("CLAUDE_CODE_SUBAGENT_MODEL"), 6, 0)
        self._layout.addWidget(self.model_subagent, 6, 1)

        self._layout.addWidget(self._make_label("CLAUDE_CODE_EFFORT_LEVEL"), 7, 0)
        self._layout.addWidget(self.effort_level, 7, 1)

        # 行 8：工作目录
        self._layout.addWidget(self.pick_btn, 8, 0)
        self._layout.addWidget(self.project_path_edit, 8, 1)

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

    def set_provider(self, provider: str) -> None:
        preset = get_provider_preset(provider)
        is_param_enabled = preset.parameters_enabled
        is_url_editable = preset.base_url_editable

        # base_url 行：中转 provider 显示可编辑输入框
        show_base_url = is_url_editable
        self._base_url_label.setVisible(show_base_url)
        self.base_url_edit.setVisible(show_base_url)
        if show_base_url:
            self.base_url_edit.setReadOnly(False)
            self.base_url_edit.setEnabled(True)
        else:
            # 固定地址 provider：base_url 由 preset 决定，不在主界面显示
            blocker = QSignalBlocker(self.base_url_edit)
            self.base_url_edit.setText(preset.base_url if is_param_enabled else "")
            del blocker

        # 模型 & effort 控件
        for combo in (
            self.model_main,
            self.model_opus,
            self.model_sonnet,
            self.model_haiku,
            self.model_subagent,
            self.effort_level,
        ):
            combo.setEnabled(is_param_enabled)

        if is_param_enabled:
            self._set_combo_items(self.model_main, preset.model_options, preset.anthropic_model_default)
            self._set_combo_items(self.model_opus, preset.model_options, preset.default_opus_model_default)
            self._set_combo_items(self.model_sonnet, preset.model_options, preset.default_sonnet_model_default)
            self._set_combo_items(self.model_haiku, preset.model_options, preset.default_haiku_model_default)
            self._set_combo_items(self.model_subagent, preset.model_options, preset.subagent_model_default)
            self._set_combo_items(self.effort_level, preset.effort_level_options, preset.effort_level_default)
        else:
            blockers = [
                QSignalBlocker(self.model_main),
                QSignalBlocker(self.model_opus),
                QSignalBlocker(self.model_sonnet),
                QSignalBlocker(self.model_haiku),
                QSignalBlocker(self.model_subagent),
                QSignalBlocker(self.effort_level),
            ]
            self.model_main.clear()
            self.model_opus.clear()
            self.model_sonnet.clear()
            self.model_haiku.clear()
            self.model_subagent.clear()
            self.effort_level.clear()
            del blockers

    def apply_config(self, config: AppConfig) -> None:
        provider = config.provider if config.provider in PROVIDER_OPTIONS else DEFAULT_PROVIDER

        blocker = QSignalBlocker(self.provider_combo)
        idx = self.provider_combo.findText(provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        else:
            self.provider_combo.setCurrentIndex(0)
        del blocker

        self.set_provider(self.provider_combo.currentText())

        preset = get_provider_preset(self.provider_combo.currentText())

        if preset.parameters_enabled:
            self.base_url_edit.setText(config.base_url.strip() or preset.base_url)
            self.model_main.setCurrentText(config.anthropic_model.strip() or preset.anthropic_model_default)
            self.model_opus.setCurrentText(
                config.default_opus_model.strip() or preset.default_opus_model_default
            )
            self.model_sonnet.setCurrentText(
                config.default_sonnet_model.strip() or preset.default_sonnet_model_default
            )
            self.model_haiku.setCurrentText(
                config.default_haiku_model.strip() or preset.default_haiku_model_default
            )
            self.model_subagent.setCurrentText(
                config.subagent_model.strip() or preset.subagent_model_default
            )
            self.effort_level.setCurrentText(config.effort_level.strip() or preset.effort_level_default)
        elif preset.base_url_editable:
            # 中转 provider：仅恢复 base_url
            self.base_url_edit.setText(config.base_url.strip())
        else:
            self.base_url_edit.clear()

        self.project_path_edit.setText(config.project_path)

    def collect_config_data(self) -> dict:
        return {
            "provider": self.provider_combo.currentText(),
            "base_url": self.base_url_edit.text().strip(),
            "anthropic_model": self.model_main.currentText(),
            "default_opus_model": self.model_opus.currentText(),
            "default_sonnet_model": self.model_sonnet.currentText(),
            "default_haiku_model": self.model_haiku.currentText(),
            "subagent_model": self.model_subagent.currentText(),
            "effort_level": self.effort_level.currentText(),
            "project_path": self.project_path_edit.text().strip(),
        }

    def set_project_path(self, path: str) -> None:
        self.project_path_edit.setText(path)
