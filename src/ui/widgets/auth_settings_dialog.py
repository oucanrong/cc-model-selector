# 路径: src/ui/widgets/auth_settings_dialog.py
# 作用: Claude Code 与 Codex 分标签管理 Base URL 和 API Key

from __future__ import annotations

import webbrowser

from PyQt6.QtGui import QColor, QFocusEvent, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.config_manager import CodexProviderSettings, ProviderSettings
from src.core.constants import (
    CODEX_PROVIDER_DEEPSEEK,
    CODEX_PROVIDER_DEFAULTS,
    CODEX_PROVIDER_ARK_CODING,
    CODEX_PROVIDER_GPT_RELAY,
    CODEX_PROVIDER_KIMI,
    CODEX_PROVIDER_MINIMAX,
    CODEX_PROVIDER_QWEN,
    CODEX_PROVIDER_XIAOMI_MIMO,
    CODEX_PROVIDER_ZHIPU,
    PROVIDER_ARK_CODING,
    PROVIDER_CLAUDE_RELAY,
    PROVIDER_DEEPSEEK,
    PROVIDER_KIMI,
    PROVIDER_MINIMAX,
    PROVIDER_QWEN,
    PROVIDER_XIAOMI_MIMO,
    PROVIDER_ZHIPU,
    get_provider_preset,
)


_API_APPLY_URLS = {
    PROVIDER_DEEPSEEK: "https://platform.deepseek.com/api_keys",
    PROVIDER_KIMI: "https://platform.moonshot.cn/console/api-keys",
    PROVIDER_ZHIPU: "https://bigmodel.cn/apikey/platform",
    PROVIDER_QWEN: "https://help.aliyun.com/zh/model-studio/get-api-key",
    PROVIDER_MINIMAX: "https://platform.minimaxi.com/console/access",
    PROVIDER_XIAOMI_MIMO: "https://platform.xiaomimimo.com/#/console/api-keys",
    PROVIDER_ARK_CODING: "https://www.volcengine.com/docs/82379/1928262",
}

_CODEX_API_APPLY_URLS = {
    CODEX_PROVIDER_DEEPSEEK: "https://platform.deepseek.com/api_keys",
    CODEX_PROVIDER_KIMI: "https://platform.moonshot.cn/console/api-keys",
    CODEX_PROVIDER_ZHIPU: "https://bigmodel.cn/apikey/platform",
    CODEX_PROVIDER_QWEN: "https://help.aliyun.com/zh/model-studio/get-api-key",
    CODEX_PROVIDER_MINIMAX: "https://platform.minimaxi.com/console/access",
    CODEX_PROVIDER_XIAOMI_MIMO: "https://platform.xiaomimimo.com/#/console/api-keys",
    CODEX_PROVIDER_ARK_CODING: "https://www.volcengine.com/docs/82379/1928262",
}

_BASE_URL_PLACEHOLDERS = {
    PROVIDER_CLAUDE_RELAY: "https://api.example.com",
    CODEX_PROVIDER_GPT_RELAY: "https://api.example.com/v1",
}


class _BaseUrlLineEdit(QLineEdit):
    def __init__(self) -> None:
        super().__init__()
        self._example_placeholder = ""
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#8a8a8a"))
        self.setPalette(palette)

    def set_example_placeholder(self, text: str) -> None:
        self._example_placeholder = text
        self.setPlaceholderText(text)

    def focusInEvent(self, event: QFocusEvent) -> None:
        if not self.text():
            self.setPlaceholderText("")
        super().focusInEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        super().focusOutEvent(event)
        if not self.text():
            self.setPlaceholderText(self._example_placeholder)


class AuthSettingsDialog(QDialog):
    def __init__(
        self,
        provider_settings: dict[str, ProviderSettings],
        codex_settings: dict[str, CodexProviderSettings],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("鉴权设置")
        self.setModal(True)
        screen = None
        if parent:
            screen = parent.screen()
        if not screen:
            screen = QApplication.primaryScreen()

        if screen:
            avail = screen.availableGeometry()
            w = min(860, int(avail.width() * 0.75))
            h = min(760, int(avail.height() * 0.85))
        else:
            w, h = 860, 760
        self.resize(w, h)
        self.setMinimumSize(min(w, 820), min(h, 700))
        self._claude_fields: dict[str, tuple[QLineEdit, QLineEdit]] = {}
        self._codex_fields: dict[str, tuple[QLineEdit, QLineEdit]] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(10)

        tabs = QTabWidget()
        tabs.setObjectName("authProductTabs")
        tabs.setTabPosition(QTabWidget.TabPosition.North)
        tabs.tabBar().setExpanding(False)
        tabs.tabBar().setFixedHeight(36)
        tabs.addTab(self._build_claude_page(provider_settings), "Claude Code")
        tabs.addTab(self._build_codex_page(codex_settings), "Codex")
        root.addWidget(tabs, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("取消")
        cancel.setObjectName("authDialogCancelButton")
        cancel.clicked.connect(self.reject)
        confirm = QPushButton("确认")
        confirm.setObjectName("authDialogConfirmButton")
        confirm.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(confirm)
        root.addLayout(buttons)
        self._apply_styles()

    def _build_claude_page(
        self,
        provider_settings: dict[str, ProviderSettings],
    ) -> QWidget:
        tabs = [
            ("DeepSeek", PROVIDER_DEEPSEEK),
            ("Kimi", PROVIDER_KIMI),
            ("智谱GLM", PROVIDER_ZHIPU),
            ("阿里千问", PROVIDER_QWEN),
            ("MiniMax", PROVIDER_MINIMAX),
            ("小米MiMo", PROVIDER_XIAOMI_MIMO),
            ("方舟Coding Plan", PROVIDER_ARK_CODING),
            ("Claude中转", PROVIDER_CLAUDE_RELAY),
        ]
        return self._build_provider_pages(
            tabs,
            provider_settings,
            self._claude_fields,
            lambda key: get_provider_preset(key).base_url,
            _API_APPLY_URLS,
        )

    def _build_codex_page(
        self,
        codex_settings: dict[str, CodexProviderSettings],
    ) -> QWidget:
        tabs = [
            ("DeepSeek", CODEX_PROVIDER_DEEPSEEK),
            ("Kimi", CODEX_PROVIDER_KIMI),
            ("智谱GLM", CODEX_PROVIDER_ZHIPU),
            ("阿里千问", CODEX_PROVIDER_QWEN),
            ("MiniMax", CODEX_PROVIDER_MINIMAX),
            ("小米MiMo", CODEX_PROVIDER_XIAOMI_MIMO),
            ("方舟Coding Plan", CODEX_PROVIDER_ARK_CODING),
            ("GPT中转", CODEX_PROVIDER_GPT_RELAY),
        ]
        return self._build_provider_pages(
            tabs,
            codex_settings,
            self._codex_fields,
            lambda key: str(CODEX_PROVIDER_DEFAULTS[key]["base_url"]),
            _CODEX_API_APPLY_URLS,
        )

    def _build_provider_pages(
        self,
        tabs,
        settings,
        fields,
        default_url,
        apply_urls,
    ) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        nav = QListWidget()
        nav.setObjectName("authTabList")
        nav.setFixedWidth(170)
        nav.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Expanding,
        )
        stack = QStackedWidget()
        for label, key in tabs:
            nav.addItem(label)
            setting = settings.get(key)
            page = QWidget()
            layout = QVBoxLayout(page)
            form = QFormLayout()
            base_url = _BaseUrlLineEdit()
            saved_url = (setting.base_url if setting else "").strip()
            placeholder = _BASE_URL_PLACEHOLDERS.get(key, "")
            if placeholder:
                base_url.setText(saved_url)
                base_url.set_example_placeholder(placeholder)
            else:
                base_url.setText(saved_url or default_url(key))
            token = QLineEdit()
            token.setEchoMode(QLineEdit.EchoMode.Password)
            token.setText((setting.token if setting else "").strip())
            form.addRow("Base URL", base_url)
            form.addRow("API Key", token)
            layout.addLayout(form)
            button_row = QHBoxLayout()
            if key in apply_urls:
                apply_button = QPushButton("申请API")
                apply_button.setObjectName("authApplyButton")
                apply_button.clicked.connect(
                    lambda _checked=False, url=apply_urls[key]: webbrowser.open(url, new=2)
                )
                button_row.addWidget(apply_button)
            button_row.addStretch(1)
            layout.addLayout(button_row)
            layout.addStretch(1)
            fields[key] = (base_url, token)
            stack.addWidget(page)
        nav.currentRowChanged.connect(stack.setCurrentIndex)
        nav.setCurrentRow(0)
        row.addWidget(nav)
        row.addWidget(stack, 1)
        return container

    def get_provider_settings(self) -> dict[str, ProviderSettings]:
        return {
            key: ProviderSettings(
                base_url=base_url.text().strip(),
                token=token.text().strip(),
            )
            for key, (base_url, token) in self._claude_fields.items()
        }

    def get_codex_settings(self) -> dict[str, CodexProviderSettings]:
        return {
            key: CodexProviderSettings(
                base_url=base_url.text().strip(),
                token=token.text().strip(),
            )
            for key, (base_url, token) in self._codex_fields.items()
        }

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QDialog { background: #ffffff; }
            QTabWidget#authProductTabs::pane {
                border: 1px solid #d9d9d9;
                border-radius: 8px;
                background: #ffffff;
            }
            QTabWidget#authProductTabs QTabBar::tab {
                background: #eef2f5;
                color: #273142;
                min-width: 92px;
                min-height: 24px;
                padding: 5px 12px;
                margin-right: 3px;
                border: 1px solid #d2d8df;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 600;
            }
            QTabWidget#authProductTabs QTabBar::tab:hover:!selected {
                background: #dff3e4;
                color: #1f6f32;
            }
            QTabWidget#authProductTabs QTabBar::tab:selected {
                background: #2ea043;
                color: #ffffff;
            }
            QListWidget#authTabList {
                background: #f7f7f7;
                border: 1px solid #d9d9d9;
                border-radius: 8px;
                outline: none;
            }
            QListWidget#authTabList::item {
                padding: 2px 8px;
                margin: 1px 3px;
                border-radius: 4px;
                color: #222222;
            }
            QListWidget#authTabList::item:selected {
                background: #2ea043;
                color: #ffffff;
            }
            QPushButton {
                border: none;
                border-radius: 8px;
                padding: 6px 16px;
                min-height: 28px;
                color: white;
            }
            QPushButton#authDialogCancelButton { background: #6e7681; }
            QPushButton#authDialogConfirmButton,
            QPushButton#authApplyButton { background: #2ea043; }
            QPushButton#authDialogConfirmButton:hover,
            QPushButton#authApplyButton:hover { background: #238636; }
            QPushButton#authDialogConfirmButton:pressed,
            QPushButton#authApplyButton:pressed { background: #196c2e; }
            QLineEdit {
                background: #ffffff;
                color: #222222;
                border: 1px solid #cfcfcf;
                border-radius: 6px;
                padding: 4px 7px;
                min-height: 28px;
            }
            """
        )
