# 路径: src/ui/widgets/auth_settings_dialog.py
# 作用: 鉴权设置弹窗
#   - DeepSeek / Kimi / 智谱GML：base_url 可编辑，保留预设默认值；API Key 可填。
#   - Claude中转 / GPT中转：base_url 可编辑（用户自填中转地址）；API Key 可填。
#   - Claude官方接口：不在此弹窗中出现。

from __future__ import annotations

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.constants import (
    PROVIDER_CLAUDE_RELAY,
    PROVIDER_DEEPSEEK,
    PROVIDER_GPT_RELAY,
    PROVIDER_KIMI,
    PROVIDER_ZHIPU,
    get_provider_preset,
)
from src.core.config_manager import ProviderSettings


class AuthSettingsDialog(QDialog):
    """
    鉴权设置弹窗。

    接收并返回 provider_settings（dict[str, ProviderSettings]），
    其中包含每个 provider 的 base_url 与 token。

    所有标签页均包含：
      - Base URL 输入框（可编辑；DeepSeek/Kimi/GML 预填固定默认值，中转留空由用户填写）
      - API Key  输入框（密文）
    """

    def __init__(
        self,
        provider_settings: dict[str, ProviderSettings],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("鉴权设置")
        self.setModal(True)
        self.resize(760, 460)
        self.setMinimumSize(700, 400)

        font = QFont("Microsoft YaHei")
        font.setPointSize(12)
        self.setFont(font)

        # {provider_key: (base_url_edit, token_edit)}
        self._fields: dict[str, tuple[QLineEdit, QLineEdit]] = {}

        self._build_ui(provider_settings)
        self._apply_styles()

    # ------------------------------------------------------------------
    # 构建 UI
    # ------------------------------------------------------------------

    def _build_ui(self, provider_settings: dict[str, ProviderSettings]) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        title = QLabel("为不同 Provider 单独保存鉴权值，留空表示不设置。")
        title.setWordWrap(True)
        root.addWidget(title)

        content_row = QHBoxLayout()
        content_row.setSpacing(12)

        self.tab_list = QListWidget()
        self.tab_list.setObjectName("authTabList")
        self.tab_list.setFixedWidth(160)
        self.tab_list.setSpacing(4)
        self.tab_list.setAlternatingRowColors(False)
        self.tab_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

        self.stack = QStackedWidget()
        self.stack.setObjectName("authPageStack")

        # 标签页列表：(显示名, provider_key)
        # Claude官方接口不在鉴权弹窗中出现（无需 API 鉴权）
        tabs: list[tuple[str, str]] = [
            ("DeepSeek",  PROVIDER_DEEPSEEK),
            ("Kimi",      PROVIDER_KIMI),
            ("GML",       PROVIDER_ZHIPU),
            ("Claude中转", PROVIDER_CLAUDE_RELAY),
            ("GPT中转",    PROVIDER_GPT_RELAY),
        ]

        for tab_label, provider_key in tabs:
            item = QListWidgetItem(tab_label)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setSizeHint(QSize(120, 44))
            self.tab_list.addItem(item)
            ps = provider_settings.get(provider_key, ProviderSettings())
            self.stack.addWidget(self._make_page(provider_key, ps))

        self.tab_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.tab_list.setCurrentRow(0)

        content_row.addWidget(self.tab_list)
        content_row.addWidget(self.stack, 1)
        root.addLayout(content_row, 1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("authDialogCancelButton")
        self.cancel_btn.clicked.connect(self.reject)

        self.confirm_btn = QPushButton("确认")
        self.confirm_btn.setObjectName("authDialogConfirmButton")
        self.confirm_btn.clicked.connect(self.accept)

        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        button_row.addWidget(self.cancel_btn)
        button_row.addWidget(self.confirm_btn)
        root.addLayout(button_row)

    def _make_page(self, provider_key: str, ps: ProviderSettings) -> QWidget:
        """
        每个标签页均包含：
          - Base URL（可编辑输入框；固定 provider 预填默认值，中转留空）
          - API Key （密文输入框）
        """
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        preset = get_provider_preset(provider_key)

        # Base URL 输入框：可编辑
        # 优先使用上次保存的值，否则用预设默认值
        saved_base_url = ps.base_url.strip()
        initial_url = saved_base_url if saved_base_url else preset.base_url

        base_url_edit = QLineEdit()
        base_url_edit.setMinimumHeight(30)
        if preset.base_url:
            base_url_edit.setPlaceholderText(preset.base_url)
        else:
            base_url_edit.setPlaceholderText("https://your-relay-host/...")
        base_url_edit.setText(initial_url)
        form.addRow("Base URL", base_url_edit)

        # API Key 输入框
        token_edit = QLineEdit()
        token_edit.setMinimumHeight(30)
        token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        token_edit.setPlaceholderText("可留空")
        token_edit.setText(ps.token.strip())
        form.addRow("API Key", token_edit)

        layout.addLayout(form)
        layout.addStretch(1)

        self._fields[provider_key] = (base_url_edit, token_edit)
        return page

    # ------------------------------------------------------------------
    # 结果获取
    # ------------------------------------------------------------------

    def get_provider_settings(self) -> dict[str, ProviderSettings]:
        """返回所有已编辑的 ProviderSettings（仅鉴权弹窗覆盖的 providers）。"""
        result: dict[str, ProviderSettings] = {}
        for provider_key, (base_url_edit, token_edit) in self._fields.items():
            result[provider_key] = ProviderSettings(
                base_url=base_url_edit.text().strip(),
                token=token_edit.text().strip(),
            )
        return result

    def get_auth_tokens(self) -> dict[str, str]:
        """向后兼容：仅返回 token 字典。"""
        return {k: v.token for k, v in self.get_provider_settings().items()}

    # ------------------------------------------------------------------
    # 样式
    # ------------------------------------------------------------------

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QDialog {
                background-color: #ffffff;
            }
            QListWidget#authTabList {
                background-color: #f7f7f7;
                border: 1px solid #d9d9d9;
                border-radius: 8px;
                outline: none;
            }
            QListWidget#authTabList::item {
                color: #222222;
                background-color: transparent;
                border: none;
                border-radius: 8px;
                padding: 10px 12px;
                margin: 4px;
            }
            QListWidget#authTabList::item:selected {
                background-color: #2ea043;
                color: white;
            }
            QListWidget#authTabList::item:hover:!selected {
                background-color: #e9f5ec;
            }
            QWidget#authPageStack {
                background-color: #ffffff;
            }
            QPushButton {
                border: none;
                border-radius: 8px;
                padding: 6px 16px;
                min-height: 28px;
                color: white;
            }
            QPushButton#authDialogCancelButton {
                background-color: #6e7681;
            }
            QPushButton#authDialogConfirmButton {
                background-color: #2ea043;
            }
            QLineEdit {
                background-color: #ffffff;
                color: #222222;
                border: 1px solid #cfcfcf;
                border-radius: 6px;
                padding: 3px 6px;
                min-height: 26px;
            }
            QLabel {
                color: #222222;
            }
            """
        )
