# 路径: C:\Users\oucan\Documents\vscode\claude_code启动器\src\ui\main_window.py
# 作用: 主窗口与交互逻辑（修复 Provider 切换时代理参数串扰，升级功能独立为按钮）

from __future__ import annotations

import copy
import webbrowser
from pathlib import Path

from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtGui import (
    QCloseEvent,
    QDesktopServices,
    QFont,
    QResizeEvent,
    QShowEvent,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.config_manager import (
    AppConfig,
    CodexModelReasoningSettings,
    CodexProviderSettings,
    ConfigManager,
    ProxyConfig,
    ProxyItem,
    ProviderSettings,
)
from src.core.constants import (
    APP_NAME,
    CODEX_PROVIDER_DEFAULTS,
    CODEX_PROVIDER_OFFICIAL,
    CODEX_REASONING_CONTROL_EFFORT,
    CODEX_REASONING_CONTROL_TOGGLE,
    PROVIDER_CLAUDE_DEFAULT,
    PROVIDER_CLAUDE_RELAY,
    get_codex_reasoning_defaults,
)
from src.core.logger import setup_logger
from src.core.process_manager import ProcessManager
from src.ui.styles import APP_QSS
from src.ui.widgets.auth_settings_dialog import AuthSettingsDialog
from src.ui.widgets.codex_parameter_group import CodexParameterGroup
from src.ui.widgets.log_console import LogConsole
from src.ui.widgets.parameter_group import ParameterGroup
from src.ui.widgets.proxy_group import ProxyGroup
from src.workers.claude_worker import ClaudeWorker
from src.workers.codex_worker import CodexWorker
from src.services.codex_config_service import CodexConfigService
from src.services.codex_service import CODEX_STORE_SEARCH_URI, CodexService
from src.services.claude_service import ClaudeService
from src.services.claude_settings_service import ClaudeSettingsService
from src.services.proxy_service import codex_has_only_socks5
from src.services.vscode_service import VSCODE_DOWNLOAD_URL, VSCodeService

# 中转 Provider 集合（需要 base_url 非空校验）
_RELAY_PROVIDERS = {PROVIDER_CLAUDE_RELAY}

# 退出确认弹窗按钮的样式（修复全局 QPushButton color:white 导致按钮文字不可见的问题）
_CONFIRM_DIALOG_BUTTON_QSS = """
QPushButton {
    color: #222222;
    background-color: #f0f0f0;
    border: 1px solid #cccccc;
    border-radius: 6px;
    padding: 5px 18px;
    min-height: 28px;
    min-width: 72px;
    font-size: 12pt;
}
QPushButton:hover {
    background-color: #e0e0e0;
}
QPushButton:pressed {
    background-color: #d0d0d0;
}
QPushButton:default {
    color: #ffffff;
    background-color: #d73a49;
    border: 1px solid #b02030;
}
QPushButton:default:hover {
    background-color: #c0323f;
}
"""


def _ask_force_quit(parent: QWidget) -> bool:
    """
    自定义退出确认弹窗，避免全局 QPushButton { color: white } 导致系统弹窗按钮文字不可见。
    返回 True 表示用户确认强制退出，False 表示取消。
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle("确认退出")
    dialog.setModal(True)
    dialog.setMinimumWidth(360)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(24, 20, 24, 16)
    layout.setSpacing(16)

    msg = QLabel("Claude Code 或 Codex 仍在运行，是否强制停止并退出？")
    msg.setWordWrap(True)
    msg.setStyleSheet("color: #222222; font-size: 12pt;")
    layout.addWidget(msg)

    btn_row = QHBoxLayout()
    btn_row.addStretch(1)

    cancel_btn = QPushButton("取消")
    cancel_btn.setStyleSheet(_CONFIRM_DIALOG_BUTTON_QSS)
    cancel_btn.clicked.connect(dialog.reject)

    confirm_btn = QPushButton("强制退出")
    confirm_btn.setDefault(True)
    confirm_btn.setStyleSheet(_CONFIRM_DIALOG_BUTTON_QSS)
    confirm_btn.clicked.connect(dialog.accept)

    btn_row.addWidget(cancel_btn)
    btn_row.addWidget(confirm_btn)
    layout.addLayout(btn_row)

    return dialog.exec() == QDialog.DialogCode.Accepted


def _show_info_dialog(parent: QWidget, title: str, message: str) -> None:
    """
    自定义信息弹窗，修复全局样式导致按钮文字白色不可见的问题。
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setModal(True)
    dialog.setMinimumWidth(420)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(24, 20, 24, 16)
    layout.setSpacing(16)

    msg = QLabel(message)
    msg.setWordWrap(True)
    msg.setStyleSheet("color: #222222; font-size: 12pt;")
    layout.addWidget(msg)

    btn_row = QHBoxLayout()
    btn_row.addStretch(1)

    confirm_btn = QPushButton("确认")
    confirm_btn.setDefault(True)
    confirm_btn.setStyleSheet(_CONFIRM_DIALOG_BUTTON_QSS)
    confirm_btn.clicked.connect(dialog.accept)

    btn_row.addWidget(confirm_btn)
    layout.addLayout(btn_row)

    dialog.exec()


def _show_confirm_dialog(parent: QWidget, title: str, message: str) -> bool:
    """
    自定义确认/取消弹窗，修复全局样式导致按钮文字白色不可见的问题。
    返回 True 表示用户点击了确认。
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setModal(True)
    dialog.setMinimumWidth(460)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(24, 20, 24, 16)
    layout.setSpacing(16)

    msg = QLabel(message)
    msg.setWordWrap(True)
    msg.setStyleSheet("color: #222222; font-size: 12pt;")
    layout.addWidget(msg)

    btn_row = QHBoxLayout()
    btn_row.addStretch(1)

    cancel_btn = QPushButton("取消")
    cancel_btn.setStyleSheet(_CONFIRM_DIALOG_BUTTON_QSS)
    cancel_btn.clicked.connect(dialog.reject)

    confirm_btn = QPushButton("确认继续")
    confirm_btn.setDefault(True)
    confirm_btn.setStyleSheet(_CONFIRM_DIALOG_BUTTON_QSS)
    confirm_btn.clicked.connect(dialog.accept)

    btn_row.addWidget(cancel_btn)
    btn_row.addWidget(confirm_btn)
    layout.addLayout(btn_row)

    return dialog.exec() == QDialog.DialogCode.Accepted


class _TopAlignedTabWidget(QTabWidget):
    _CORNER_RIGHT_MARGIN = 12

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._header_widget: QWidget | None = None

    def set_header_widget(self, widget: QWidget) -> None:
        self._header_widget = widget
        widget.setParent(self)
        widget.show()
        widget.raise_()
        self._align_header_widget()

    def _align_header_widget(self) -> None:
        if self._header_widget is not None:
            self._header_widget.move(
                self.width()
                - self._header_widget.width()
                - self._CORNER_RIGHT_MARGIN,
                self.tabBar().y(),
            )
            self._header_widget.raise_()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._align_header_widget()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._align_header_widget()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            w = min(760, int(avail.width() * 0.65))
            h = min(900, int(avail.height() * 0.90))
        else:
            w, h = 760, 900
        self.resize(w, h)
        self.setMinimumSize(560, 500)

        self._apply_fonts()

        self.logger = setup_logger()
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load()
        self.process_manager = ProcessManager()
        self.codex_process_manager = ProcessManager()
        self.claude_service = ClaudeService()
        self.codex_service = CodexService()
        self.vscode_service = VSCodeService()
        self.worker: ClaudeWorker | None = None
        self.codex_worker: CodexWorker | None = None
        self._loading = False

        if CodexConfigService().recover_if_needed():
            self.logger.warning("检测到上次异常退出，已恢复 Codex config.toml。")
        if ClaudeSettingsService().recover_if_needed():
            self.logger.warning("检测到上次异常退出，已恢复 Claude settings.json。")

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(250)
        self._autosave_timer.timeout.connect(self._auto_save)

        self._build_ui()
        self._bind_config()
        self._wire_autosave()
        self._detect_external_codex_on_startup()

    def _detect_external_codex_on_startup(self) -> None:
        if self.codex_service.is_any_desktop_running():
            message = "检测到 Codex 桌面版已在运行，请关闭后再使用启动功能。"
            self.codex_status_label.setText(message)
            self.codex_log_console.append_entry("SYSTEM", message)

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)

        self.product_tabs = _TopAlignedTabWidget()
        self.product_tabs.setObjectName("mainProductTabs")
        self.product_tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.product_tabs.tabBar().setExpanding(False)
        self.product_tabs.tabBar().setFixedHeight(36)

        self.auth_btn = QPushButton("鉴权设置")
        self.auth_btn.setObjectName("authSettingsButton")
        self.auth_btn.setMinimumWidth(120)
        self.auth_btn.setFixedHeight(36)
        self.auth_btn.clicked.connect(self.open_auth_settings)
        self.product_tabs.set_header_widget(self.auth_btn)

        claude_page = QWidget()
        claude_root = QVBoxLayout(claude_page)
        claude_root.setContentsMargins(12, 12, 12, 12)
        codex_page = QWidget()
        codex_root = QVBoxLayout(codex_page)
        codex_root.setContentsMargins(12, 12, 12, 12)

        self.parameter_group = ParameterGroup(on_pick_project=self.pick_project)
        self.proxy_group = ProxyGroup()
        self.log_console = LogConsole()
        self.status_label = QLabel("就绪")
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # 安装进度条（默认隐藏，安装 Claude Code 时显示）
        self.install_progress_bar = QProgressBar()
        self.install_progress_bar.setMinimum(0)
        self.install_progress_bar.setMaximum(100)
        self.install_progress_bar.setValue(0)
        self.install_progress_bar.setTextVisible(True)
        self.install_progress_bar.setFormat("%p% %v")
        self.install_progress_bar.setMinimumHeight(22)
        self.install_progress_bar.setVisible(False)
        self.install_progress_label = QLabel("")
        self.install_progress_label.setStyleSheet("color: #0e639c; font-size: 11pt;")
        self.install_progress_label.setVisible(False)

        # ── 底部按钮 ──────────────────────────────────────────────
        self.start_btn = QPushButton("启动")
        self.start_btn.setObjectName("startButton")
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setObjectName("stopButton")
        self.copy_btn = QPushButton("复制日志")
        self.copy_btn.setObjectName("copyButton")
        self.clear_btn = QPushButton("清空日志")
        self.clear_btn.setObjectName("clearButton")
        self.reset_btn = QPushButton("重置")
        self.reset_btn.setObjectName("resetButton")
        self.exit_btn = QPushButton("退出")
        self.exit_btn.setObjectName("exitButton")

        self.start_btn.clicked.connect(self.start_selected_claude_target)
        self.stop_btn.clicked.connect(self.stop_claude)
        self.copy_btn.clicked.connect(self.copy_logs_to_clipboard)
        self.clear_btn.clicked.connect(self.log_console.clear_logs)
        self.reset_btn.clicked.connect(self.reset_form)
        self.exit_btn.clicked.connect(self.close)

        self.stop_btn.setEnabled(False)

        button_row = QHBoxLayout()
        for btn in (
            self.start_btn,
            self.stop_btn,
            self.copy_btn,
            self.clear_btn,
            self.reset_btn,
            self.exit_btn,
        ):
            btn.setMinimumWidth(112)
            button_row.addWidget(btn)

        claude_root.addWidget(self.parameter_group)
        claude_root.addWidget(self.proxy_group)
        claude_root.addWidget(QLabel("日志输出"))
        claude_root.addWidget(self.log_console, 1)
        # 进度条区域
        claude_root.addWidget(self.install_progress_bar)
        claude_root.addWidget(self.install_progress_label)
        claude_root.addWidget(self.status_label)
        claude_root.addLayout(button_row)
        claude_root.setStretchFactor(self.log_console, 1)

        self.codex_parameter_group = CodexParameterGroup(self.pick_codex_project)
        self.codex_proxy_group = ProxyGroup()
        self.codex_log_console = LogConsole()
        self.codex_status_label = QLabel("就绪")
        self.codex_start_btn = QPushButton("启动")
        self.codex_start_btn.setObjectName("startButton")
        self.codex_stop_btn = QPushButton("停止")
        self.codex_stop_btn.setObjectName("stopButton")
        self.codex_copy_btn = QPushButton("复制日志")
        self.codex_copy_btn.setObjectName("copyButton")
        self.codex_clear_btn = QPushButton("清空日志")
        self.codex_clear_btn.setObjectName("clearButton")
        self.codex_reset_btn = QPushButton("重置")
        self.codex_reset_btn.setObjectName("resetButton")
        self.codex_exit_btn = QPushButton("退出")
        self.codex_exit_btn.setObjectName("exitButton")
        self.codex_stop_btn.setEnabled(False)
        self.codex_start_btn.clicked.connect(self.start_selected_codex_target)
        self.codex_stop_btn.clicked.connect(self.stop_codex)
        self.codex_copy_btn.clicked.connect(
            lambda: QApplication.clipboard().setText(self.codex_log_console.toPlainText())
        )
        self.codex_clear_btn.clicked.connect(self.codex_log_console.clear_logs)
        self.codex_reset_btn.clicked.connect(self.reset_codex_form)
        self.codex_exit_btn.clicked.connect(self.close)
        codex_buttons = QHBoxLayout()
        for button in (
            self.codex_start_btn,
            self.codex_stop_btn,
            self.codex_copy_btn,
            self.codex_clear_btn,
            self.codex_reset_btn,
            self.codex_exit_btn,
        ):
            button.setMinimumWidth(105)
            codex_buttons.addWidget(button)
        codex_root.addWidget(self.codex_parameter_group)
        codex_root.addWidget(self.codex_proxy_group)
        codex_root.addWidget(QLabel("日志输出"))
        codex_root.addWidget(self.codex_log_console, 1)
        codex_root.addWidget(self.codex_status_label)
        codex_root.addLayout(codex_buttons)
        codex_root.setStretchFactor(self.codex_log_console, 1)

        claude_scroll = QScrollArea()
        claude_scroll.setWidgetResizable(True)
        claude_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        claude_scroll.setWidget(claude_page)
        codex_scroll = QScrollArea()
        codex_scroll.setWidgetResizable(True)
        codex_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        codex_scroll.setWidget(codex_page)
        self.product_tabs.addTab(claude_scroll, "Claude Code")
        self.product_tabs.addTab(codex_scroll, "Codex")
        root.addWidget(self.product_tabs, 1)

        self.setCentralWidget(central)
        self.setStyleSheet(APP_QSS)
        self._sync_parameter_group_layouts()

    def _sync_parameter_group_layouts(self) -> None:
        groups = (self.parameter_group, self.codex_parameter_group)
        layouts = (self.parameter_group._layout, self.codex_parameter_group._layout)
        label_width = max(
            label.sizeHint().width()
            for group in groups
            for label in group.findChildren(QLabel)
        )
        for layout in layouts:
            layout.setColumnMinimumWidth(0, label_width)

        for group in groups:
            group.setMinimumHeight(0)
            group.setMaximumHeight(16777215)
            group.layout().activate()
        target_height = max(group.sizeHint().height() for group in groups)
        for group in groups:
            group.setFixedHeight(target_height)

    def _apply_fonts(self) -> None:
        app = QApplication.instance()
        if app is not None:
            font = QFont("Microsoft YaHei")
            font.setPointSize(12)
            app.setFont(font)

    def _bind_config(self) -> None:
        self._loading = True
        try:
            self.parameter_group.apply_config(self.config)
            self.proxy_group.apply_config(self.config)
            self.codex_parameter_group.apply_config(self.config.codex)
            codex_setting = self.config.codex.provider_settings[self.config.codex.provider]
            codex_setting.proxy = copy.deepcopy(
                codex_setting.proxies[self.config.codex.launch_target]
            )
            codex_proxy_config = AppConfig(proxy=codex_setting.proxy)
            self.codex_proxy_group.apply_config(codex_proxy_config)
            self.config.token = self.config.auth_tokens.get(self.config.provider, "").strip()
        finally:
            self._loading = False
        self._sync_parameter_group_layouts()
        self._refresh_status()
        self._sync_claude_target_state()
        self._sync_codex_target_state()

    def _wire_autosave(self) -> None:
        pg = self.parameter_group
        pg.provider_combo.currentTextChanged.connect(self._handle_provider_change)
        pg.base_url_edit.textChanged.connect(self._schedule_autosave)
        pg.model_main.currentTextChanged.connect(self._schedule_autosave)
        pg.model_opus.currentTextChanged.connect(self._schedule_autosave)
        pg.model_sonnet.currentTextChanged.connect(self._schedule_autosave)
        pg.model_haiku.currentTextChanged.connect(self._schedule_autosave)
        pg.model_subagent.currentTextChanged.connect(self._schedule_autosave)
        pg.effort_level.currentTextChanged.connect(self._schedule_autosave)
        pg.launch_target_combo.currentIndexChanged.connect(
            self._handle_claude_launch_target_change
        )
        pg.project_path_edit.textChanged.connect(self._schedule_autosave)
        # Kimi / GLM5 专用参数
        pg.enable_tool_search.currentTextChanged.connect(self._schedule_autosave)
        pg.disable_nonessential_traffic.currentTextChanged.connect(self._schedule_autosave)
        pg.api_timeout_ms.textChanged.connect(self._schedule_autosave)
        pg.has_completed_onboarding.currentTextChanged.connect(self._schedule_autosave)

        for row in (self.proxy_group.http, self.proxy_group.https, self.proxy_group.socks5):
            row.enabled.toggled.connect(self._schedule_autosave)
            row.host.textChanged.connect(self._schedule_autosave)
            row.port.textChanged.connect(self._schedule_autosave)
            row.username.textChanged.connect(self._schedule_autosave)
            row.password.textChanged.connect(self._schedule_autosave)

        cpg = self.codex_parameter_group
        cpg.provider_combo.currentTextChanged.connect(self._handle_codex_provider_change)
        cpg.model_combo.currentTextChanged.connect(
            self._handle_codex_model_change
        )
        cpg.reasoning_combo.currentTextChanged.connect(self._schedule_autosave)
        cpg.thinking_combo.currentTextChanged.connect(self._schedule_autosave)
        cpg.launch_target_combo.currentIndexChanged.connect(
            self._handle_codex_launch_target_change
        )
        cpg.project_path_edit.textChanged.connect(self._schedule_autosave)
        for row in (
            self.codex_proxy_group.http,
            self.codex_proxy_group.https,
            self.codex_proxy_group.socks5,
        ):
            row.enabled.toggled.connect(self._schedule_autosave)
            row.host.textChanged.connect(self._schedule_autosave)
            row.port.textChanged.connect(self._schedule_autosave)
            row.username.textChanged.connect(self._schedule_autosave)
            row.password.textChanged.connect(self._schedule_autosave)

    def _refresh_status(self) -> None:
        self.status_label.setText(
            f"Provider: {self.config.provider} | 项目目录: {self.config.project_path or '未选择'}"
        )
        self.codex_status_label.setText(
            f"Provider: {self.config.codex.provider} | "
            f"项目目录: {self.config.codex.project_path or '未选择'}"
        )

    def _handle_claude_launch_target_change(self) -> None:
        if self._loading:
            return
        old_target = self.config.claude_launch_target
        self._sync_config_from_ui()
        setting = self.config.provider_settings[self.config.provider]
        setting.proxies[old_target] = copy.deepcopy(self.config.proxy)
        new_target = self.parameter_group.current_launch_target()
        self.config.claude_launch_target = new_target
        self.config.proxy = copy.deepcopy(setting.proxies[new_target])
        self._loading = True
        try:
            self.proxy_group.apply_config(self.config)
        finally:
            self._loading = False
        self._sync_claude_target_state()
        if new_target == "vscode":
            _show_info_dialog(
                self,
                "VS Code使用说明",
                "1. 请在VS Code中禁用或卸载Claude Code插件。"
                "如果已禁用或卸载或未安装，继续第2步。\n"
                "2. 选择工作目录。\n"
                '3. 然后在启动目标中选择"启动Claude Code cli版"，'
                "用于生成与修改项目代码。\n"
                "4. 手动运行VS Code，仅用于查看源代码与确认项目运行结果。",
            )
        self.config_manager.save(self.config)
        self._refresh_status()

    def _sync_claude_target_state(self) -> None:
        is_vscode = self.parameter_group.current_launch_target() == "vscode"
        self.start_btn.setEnabled(not is_vscode)
        self.proxy_group.set_ui_enabled(not is_vscode)

    def _handle_codex_launch_target_change(self) -> None:
        if self._loading:
            return
        old_target = self.config.codex.launch_target
        self._sync_codex_config_from_ui(proxy_target_override=old_target)
        new_target = self.codex_parameter_group.current_launch_target()
        self.config.codex.launch_target = new_target
        setting = self.config.codex.provider_settings[self.config.codex.provider]
        setting.proxy = copy.deepcopy(setting.proxies[new_target])
        self._loading = True
        try:
            self.codex_proxy_group.apply_config(AppConfig(proxy=setting.proxy))
        finally:
            self._loading = False
        self._sync_codex_target_state()
        if new_target == "vscode":
            _show_info_dialog(
                self,
                "VS Code使用说明",
                "1. 请在VS Code中禁用或卸载Codex插件。"
                "如果已禁用或卸载或未安装，继续第2步。\n"
                "2. 选择工作目录。\n"
                '3. 在启动目标中选择"启动Codex 桌面版"或'
                '"启动Codex cli版"，用于生成与修改项目代码。\n'
                "4. 手动运行VS Code，仅用于查看源代码与确认项目运行结果。",
            )
        self.config_manager.save(self.config)
        self._refresh_status()

    def _sync_codex_target_state(self) -> None:
        target = self.codex_parameter_group.current_launch_target()
        self.codex_start_btn.setEnabled(target != "vscode")
        self.codex_proxy_group.set_ui_enabled(
            target not in {"desktop", "vscode"}
        )

    def _schedule_autosave(self) -> None:
        if self._loading:
            return
        self._autosave_timer.start()

    def _handle_codex_provider_change(self, provider: str) -> None:
        if self._loading:
            return
        old_provider = self.config.codex.provider
        self._sync_codex_config_from_ui(provider_override=old_provider)
        self.config.codex.provider = provider
        self._loading = True
        try:
            self.codex_parameter_group.apply_config(self.config.codex)
            setting = self.config.codex.provider_settings[provider]
            setting.proxy = copy.deepcopy(
                setting.proxies[self.config.codex.launch_target]
            )
            self.codex_proxy_group.apply_config(AppConfig(proxy=setting.proxy))
        finally:
            self._loading = False
        self._sync_parameter_group_layouts()
        self._refresh_status()
        self._sync_codex_target_state()
        self._schedule_autosave()

    def _handle_codex_model_change(self, model: str) -> None:
        if self._loading:
            return
        provider = self.codex_parameter_group.provider_combo.currentText()
        setting = self.config.codex.provider_settings[provider]
        if not CODEX_PROVIDER_DEFAULTS[provider].get("model_reasoning"):
            setting.model = model
            self._schedule_autosave()
            return
        self._store_codex_reasoning_state(provider, setting, setting.model)
        setting.model = model
        self._load_codex_reasoning_state(provider, setting, model)
        self._loading = True
        try:
            self.codex_parameter_group.apply_reasoning_settings(
                provider,
                model,
                setting.reasoning_effort,
                setting.thinking_enabled,
            )
        finally:
            self._loading = False
        self._sync_parameter_group_layouts()
        self._schedule_autosave()

    def _handle_provider_change(self, provider: str) -> None:
        """
        Provider 切换处理。

        关键：_sync_config_from_ui() 会将 config.provider 设为 combo box
        当前值（即新 Provider），导致后续 _flush_active_provider 将旧
        Provider 的代理参数写入新 Provider 的配置中。

        修复方式：在调用 _sync_config_from_ui 前保存旧 provider，在
        _flush_active_provider 前恢复，确保旧 provider 的配置正确落盘。
        """
        # 保存旧 provider（_sync_config_from_ui 会覆盖 config.provider）
        old_provider = self.config.provider

        # 将当前 UI 数据读取到 config 顶层字段
        self._sync_config_from_ui()

        # BUGFIX: _sync_config_from_ui() 内部先将 config.provider 设为新 provider，
        # 然后从 auth_tokens[新provider] 读取 token 赋值给 config.token。
        # 必须在此处恢复为旧 provider 的 token，否则 _flush_active_provider
        # 会把新 provider 的 token（或空值）写入旧 provider 的配置中，
        # 导致旧 provider 的 API Key 被清空或串号。
        self.config.token = self.config.auth_tokens.get(old_provider, "").strip()

        # 恢复旧 provider，确保 _flush_active_provider 写入正确的条目
        self.config.provider = old_provider
        self.config_manager._flush_active_provider(self.config)

        # 切换到新 provider
        self.config.provider = provider

        # 从 provider_settings 恢复新 provider 的参数到 UI
        self._loading = True
        try:
            self.config_manager._sync_active_provider(self.config)
            self.parameter_group.apply_config(self.config)
            self.proxy_group.apply_config(self.config)
        finally:
            self._loading = False

        self._sync_parameter_group_layouts()
        self._schedule_autosave()
        self._refresh_status()
        self._sync_claude_target_state()

    def _sync_config_from_ui(self) -> AppConfig:
        data = self.parameter_group.collect_config_data()
        proxy = self.proxy_group.collect_config_data()

        self.config.provider = data["provider"]
        self.config.base_url = data["base_url"]
        self.config.token = self.config.auth_tokens.get(self.config.provider, "").strip()
        self.config.anthropic_model = data["anthropic_model"]
        self.config.default_opus_model = data["default_opus_model"]
        self.config.default_sonnet_model = data["default_sonnet_model"]
        self.config.default_haiku_model = data["default_haiku_model"]
        self.config.subagent_model = data["subagent_model"]
        self.config.effort_level = data["effort_level"]
        self.config.claude_launch_target = data["launch_target"]
        self.config.project_path = data["project_path"]
        # Kimi / GLM5 专用参数
        self.config.enable_tool_search = data["enable_tool_search"]
        self.config.disable_nonessential_traffic = data["disable_nonessential_traffic"]
        self.config.api_timeout_ms = data["api_timeout_ms"]
        self.config.has_completed_onboarding = data["has_completed_onboarding"]

        self.config.proxy.http = ProxyItem(**proxy["http"])
        self.config.proxy.https = ProxyItem(**proxy["https"])
        self.config.proxy.socks5 = ProxyItem(**proxy["socks5"])

        if self.config.project_path.strip():
            history = [p for p in self.config.recent_projects if p != self.config.project_path]
            history.insert(0, self.config.project_path)
            self.config.recent_projects = history[:10]

        return self.config

    def _auto_save(self) -> None:
        if self._loading:
            return
        self._sync_config_from_ui()
        self._sync_codex_config_from_ui()
        self.config_manager.save(self.config)
        self._refresh_status()

    def open_auth_settings(self) -> None:
        dialog = AuthSettingsDialog(
            self.config.provider_settings,
            self.config.codex.provider_settings,
            self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        # 把鉴权弹窗中修改的 base_url + token 合并回 provider_settings
        new_settings = dialog.get_provider_settings()
        for provider_key, ps_new in new_settings.items():
            existing = self.config.provider_settings.get(provider_key, ProviderSettings())
            # 只更新 base_url 和 token，保留其他字段
            existing.base_url = ps_new.base_url
            existing.token = ps_new.token
            self.config.provider_settings[provider_key] = existing
            # 同步 auth_tokens 向后兼容字段
            self.config.auth_tokens[provider_key] = ps_new.token

        for provider_key, new_setting in dialog.get_codex_settings().items():
            existing = self.config.codex.provider_settings.get(
                provider_key,
                CodexProviderSettings(),
            )
            existing.base_url = new_setting.base_url
            existing.token = new_setting.token
            self.config.codex.provider_settings[provider_key] = existing

        # 若当前激活的 provider 被修改，更新快捷字段
        if self.config.provider in new_settings:
            ps_cur = self.config.provider_settings[self.config.provider]
            self.config.token = ps_cur.token
            # 若 base_url 可编辑，更新 UI 中的 base_url
            from src.core.constants import get_provider_preset
            preset = get_provider_preset(self.config.provider)
            if preset.base_url_editable:
                self._loading = True
                try:
                    self.parameter_group.base_url_edit.setText(ps_cur.base_url)
                finally:
                    self._loading = False

        self.config_manager.save(self.config)
        self.status_bar.showMessage("鉴权设置已保存", 3000)
        self._refresh_status()

    def pick_project(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择 Claude 工作目录")
        if directory:
            self.parameter_group.set_project_path(directory)
            self._schedule_autosave()

    def pick_codex_project(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择 Codex 工作目录")
        if directory:
            self.codex_parameter_group.project_path_edit.setText(directory)
            self._schedule_autosave()

    def _sync_codex_config_from_ui(
        self,
        provider_override: str | None = None,
        proxy_target_override: str | None = None,
    ) -> None:
        provider = provider_override or self.codex_parameter_group.provider_combo.currentText()
        setting = self.config.codex.provider_settings.setdefault(
            provider,
            CodexProviderSettings(),
        )
        if provider != CODEX_PROVIDER_OFFICIAL:
            model = self.codex_parameter_group.model_combo.currentText()
            setting.model = model
            self._store_codex_reasoning_state(provider, setting, model)
        proxy_data = self.codex_proxy_group.collect_config_data()
        setting.proxy = ProxyConfig(
            http=ProxyItem(**proxy_data["http"]),
            https=ProxyItem(**proxy_data["https"]),
            socks5=ProxyItem(**proxy_data["socks5"]),
        )
        proxy_target = proxy_target_override or self.config.codex.launch_target
        setting.proxies[proxy_target] = copy.deepcopy(setting.proxy)
        setting.proxies["desktop"] = ProxyConfig()
        setting.proxies["vscode"] = ProxyConfig()
        self.config.codex.provider = self.codex_parameter_group.provider_combo.currentText()
        self.config.codex.launch_target = (
            self.codex_parameter_group.current_launch_target()
        )
        self.config.codex.project_path = self.codex_parameter_group.project_path_edit.text().strip()
        if self.config.codex.project_path:
            history = [
                path
                for path in self.config.codex.recent_projects
                if path != self.config.codex.project_path
            ]
            self.config.codex.recent_projects = [
                self.config.codex.project_path,
                *history,
            ][:10]

    def _store_codex_reasoning_state(
        self,
        provider: str,
        setting: CodexProviderSettings,
        model: str,
    ) -> None:
        defaults = get_codex_reasoning_defaults(provider, model)
        control = defaults["reasoning_control"]
        setting.reasoning_effort = (
            self.codex_parameter_group.current_reasoning_effort()
            if control == CODEX_REASONING_CONTROL_EFFORT
            else ""
        )
        if control == CODEX_REASONING_CONTROL_TOGGLE:
            setting.thinking_enabled = (
                self.codex_parameter_group.current_thinking_enabled()
            )
        if model in CODEX_PROVIDER_DEFAULTS[provider].get("model_reasoning", {}):
            setting.model_reasoning[model] = CodexModelReasoningSettings(
                reasoning_effort=setting.reasoning_effort,
                thinking_enabled=setting.thinking_enabled,
            )

    @staticmethod
    def _load_codex_reasoning_state(
        provider: str,
        setting: CodexProviderSettings,
        model: str,
    ) -> None:
        defaults = get_codex_reasoning_defaults(provider, model)
        saved = setting.model_reasoning.get(model)
        setting.reasoning_effort = (
            saved.reasoning_effort
            if saved is not None
            else str(defaults["default_reasoning_effort"])
        )
        setting.thinking_enabled = (
            saved.thinking_enabled
            if saved is not None
            else bool(defaults["default_thinking_enabled"])
        )

    def copy_logs_to_clipboard(self) -> None:
        QApplication.clipboard().setText(self.log_console.toPlainText())
        self.status_bar.showMessage("日志已复制到剪贴板", 3000)

    def reset_form(self) -> None:
        if self.process_manager.running:
            QMessageBox.information(self, "提示", "Claude 正在运行，不能重置。")
            return
        self._loading = True
        try:
            # 保留当前 provider，重置后不跳转
            preserved_provider = self.config.provider
            preserved_vscode_path = self.config.vscode_path
            # 保留鉴权信息（auth_tokens + provider_settings 中的 base_url/token）
            preserved_tokens = dict(self.config.auth_tokens)
            preserved_provider_settings: dict[str, ProviderSettings] = {}
            for pk, ps in self.config.provider_settings.items():
                preserved_provider_settings[pk] = ProviderSettings(
                    base_url=ps.base_url,
                    token=ps.token,
                    # 其余参数重置为空，让 _sync_active_provider 使用预设默认值
                    anthropic_model="",
                    default_opus_model="",
                    default_sonnet_model="",
                    default_haiku_model="",
                    subagent_model="",
                    effort_level="",
                    api_timeout_ms="",
                    proxy=ProxyConfig(),
                )

            self.config = AppConfig(
                provider=preserved_provider,
                auth_tokens=preserved_tokens,
                provider_settings=preserved_provider_settings,
                vscode_path=preserved_vscode_path,
                # project_path 重置为空
                project_path="",
            )
            # 同步当前 provider 的 top-level 字段（用预设默认值填充空字段，恢复保留的 base_url/token）
            self.config_manager._sync_active_provider(self.config)
            self.parameter_group.apply_config(self.config)
            self.proxy_group.apply_config(self.config)
            self.log_console.clear_logs()
            self.config_manager.save(self.config)
        finally:
            self._loading = False
        self._refresh_status()
        self._sync_claude_target_state()

    def reset_codex_form(self) -> None:
        if self.codex_process_manager.running:
            QMessageBox.information(self, "提示", "Codex 正在运行，不能重置。")
            return
        provider = self.config.codex.provider
        current = self.config.codex.provider_settings[provider]
        defaults = CODEX_PROVIDER_DEFAULTS[provider]
        current.model = str(defaults["default_model"])
        current.model_reasoning = {}
        for model in defaults.get("model_reasoning", {}):
            reasoning = get_codex_reasoning_defaults(provider, model)
            current.model_reasoning[model] = CodexModelReasoningSettings(
                reasoning_effort=str(reasoning["default_reasoning_effort"]),
                thinking_enabled=bool(reasoning["default_thinking_enabled"]),
            )
        self._load_codex_reasoning_state(provider, current, current.model)
        current.proxies = {
            target: ProxyConfig()
            for target in current.proxies
        }
        current.proxy = ProxyConfig()
        self.config.codex.launch_target = "desktop"
        self.config.codex.project_path = ""
        self._loading = True
        try:
            self.codex_parameter_group.apply_config(self.config.codex)
            self.codex_proxy_group.apply_config(AppConfig(proxy=current.proxy))
            self.codex_log_console.clear_logs()
        finally:
            self._loading = False
        self.config_manager.save(self.config)
        self._refresh_status()
        self._sync_codex_target_state()

    def _validate_proxy_config(self) -> bool:
        """
        调用 ProxyGroup.validate() 校验代理配置。
        校验失败时弹窗提示用户，返回 False；通过返回 True。
        """
        ok, msg = self.proxy_group.validate()
        if not ok:
            _show_info_dialog(self, "代理配置不完整", msg)
        return ok

    def _check_proxy_for_official(self) -> bool:
        """
        当 Provider 为 Claude官方接口 时，检测代理是否为空。
        若代理为空，弹窗提示用户确认后继续启动。
        返回 True 表示可以继续启动，False 表示用户取消。
        """
        proxy = self.proxy_group
        has_proxy = (
            (proxy.http.enabled.isChecked() and proxy.http.host.text().strip())
            or (proxy.https.enabled.isChecked() and proxy.https.host.text().strip())
            or (proxy.socks5.enabled.isChecked() and proxy.socks5.host.text().strip())
        )
        if has_proxy:
            return True

        # 代理参数为空，弹窗提示
        msg = (
            "如果不勾选 HTTP 和 HTTPS 代理，有可能导致 Claude Code 运行异常或闪退。\n"
            "点击确认继续，无代理启动 Claude Code。"
        )
        return _show_confirm_dialog(self, "代理提示", msg)

    # ------------------------------------------------------------------
    # 启动 Claude Code
    # ------------------------------------------------------------------

    def start_selected_claude_target(self) -> None:
        target = self.parameter_group.current_launch_target()
        if target == "upgrade":
            self.upgrade_claude()
        elif target == "cli":
            self.start_claude()

    def start_claude(self) -> None:
        self._start_claude_target()

    def _resolve_vscode_for_launch(self) -> Path | None:
        executable = self.vscode_service.resolve_executable(self.config.vscode_path)
        if executable is not None:
            if self.config.vscode_path != str(executable):
                self.config.vscode_path = str(executable)
                self.config_manager.save(self.config)
            return executable

        webbrowser.open(VSCODE_DOWNLOAD_URL, new=2)
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "选择 VS Code 程序",
            "",
            "VS Code (Code.exe)",
        )
        if not selected:
            _show_info_dialog(
                self,
                "未找到 VS Code",
                "未检测到 VS Code，已打开官方下载页面。"
                "安装完成后请重新点击启动VS Code。",
            )
            return None
        candidate = Path(selected)
        if candidate.name.casefold() != "code.exe" or not candidate.is_file():
            _show_info_dialog(self, "路径无效", "请选择有效的 Code.exe 文件。")
            return None
        self.config.vscode_path = str(candidate)
        self.config_manager.save(self.config)
        return candidate

    def _start_claude_target(self) -> None:
        self._auto_save()

        if self.process_manager.running:
            QMessageBox.information(self, "提示", "Claude Code 已在运行，禁止重复启动。")
            return
        if self.claude_service.is_vscode_extension_running():
            QMessageBox.information(
                self,
                "提示",
                "检测到VS Code Claude Code插件正在运行中。\n"
                "请先禁用或卸载VS Code中的Claude Code插件，然后手动重启VS Code。\n"
                '然后再选择"启动Claude Code cli版"，用于创建和修改项目代码。\n'
                "VS Code仅用于查看源代码与确认项目运行结果。",
            )
            return
        if self.claude_service.is_any_native_running():
            QMessageBox.information(
                self,
                "提示",
                "检测到 Claude Code 进程已通过其他方式启动。"
                "请先关闭该进程后再试。",
            )
            return

        # ── 校验：第三方 Provider 的 API 鉴权信息不能为空 ──────────
        if self.config.provider != PROVIDER_CLAUDE_DEFAULT:
            token = self.config.auth_tokens.get(self.config.provider, "").strip()
            if not token:
                QMessageBox.warning(
                    self,
                    "鉴权信息缺失",
                    f"当前 Provider 为【{self.config.provider}】，尚未填写 API Token。\n\n"
                    "请点击右上角「鉴权设置」按钮，为该 Provider 填入对应的 API Key 后再启动。",
                )
                return

        # ── 校验：项目目录不能为空 ──────────────────────────────────
        try:
            validate_path = self.parameter_group.project_path_edit.text().strip()
            if not validate_path:
                raise ValueError("项目目录不存在或不是有效目录。")
        except Exception as exc:
            QMessageBox.warning(self, "校验失败", str(exc))
            return

        # ── 校验：代理配置（勾选必须填 IP + 端口） ──────────────────
        if not self._validate_proxy_config():
            return

        # ── Claude官方接口：代理为空时提示确认 ─────────────────────
        if self.config.provider == PROVIDER_CLAUDE_DEFAULT:
            if not self._check_proxy_for_official():
                return

        target_name = "Claude Code CLI"
        self.status_label.setText(f"正在启动 {target_name} ...")
        self.log_console.append_entry("SYSTEM", f"正在启动 {target_name} ...")

        # ── 锁定 UI ──────────────────────────────────────────────
        self._lock_claude_ui()

        self.worker = ClaudeWorker(
            self.config,
            self.process_manager,
            upgrade_only=False,
        )
        self.worker.log_signal.connect(self.log_console.append_process_output)
        self.worker.status_signal.connect(self._update_status)
        self.worker.error_signal.connect(self._on_worker_error)
        self.worker.finished_signal.connect(self._on_worker_finished)
        self.worker.npm_not_found_signal.connect(self._on_npm_not_found)
        self.worker.install_success_signal.connect(self._on_install_success)
        self.worker.install_progress_signal.connect(self._on_install_progress)
        self.worker.start()

    def start_selected_codex_target(self) -> None:
        target = self.codex_parameter_group.current_launch_target()
        if target == "desktop":
            self.start_codex_desktop()
        elif target == "vscode":
            self.start_codex_vscode()
        elif target == "upgrade":
            self.upgrade_codex()
        else:
            self.start_codex()

    def start_codex(self) -> None:
        self._start_codex_target("cli")

    def start_codex_desktop(self) -> None:
        self._start_codex_target("desktop")

    def start_codex_vscode(self) -> None:
        self._start_codex_target("vscode")

    def _start_codex_target(self, launch_target: str) -> None:
        self._auto_save()
        if launch_target == "vscode":
            return
        if self.codex_process_manager.running:
            QMessageBox.information(self, "提示", "Codex 已在运行，禁止重复启动。")
            return
        if (
            launch_target in {"desktop", "cli"}
            and self.codex_service.is_vscode_extension_running()
        ):
            QMessageBox.information(
                self,
                "提示",
                "检测到VS Code Codex插件正在运行中。\n"
                "请先禁用或卸载VS Code中的Codex插件，然后手动重启VS Code。\n"
                '再选择"启动Codex 桌面版"或"启动Codex cli版"，'
                "用于创建和修改项目代码。\n"
                "VS Code仅用于查看源代码与确认项目运行结果。",
            )
            return
        desktop_executable = self.codex_service.resolve_desktop_executable()
        if (
            self.codex_service.is_any_desktop_running()
            or self.codex_service.is_desktop_running(desktop_executable)
        ):
            QMessageBox.information(
                self,
                "提示",
                "检测到 Codex 桌面版已在运行，请先关闭后再启动。",
            )
            return
        if launch_target == "desktop" and desktop_executable is None:
            if _show_confirm_dialog(
                self,
                "未安装 Codex 桌面版",
                "当前用户尚未安装 Codex 桌面版。"
                "是否打开 Microsoft Store 搜索 Codex？\n\n"
                "安装和登录需要由用户在商店中手动完成。",
            ):
                QDesktopServices.openUrl(QUrl(CODEX_STORE_SEARCH_URI))
            return
        provider = self.config.codex.provider
        setting = self.config.codex.provider_settings[provider]
        if provider != CODEX_PROVIDER_OFFICIAL:
            if not setting.token.strip():
                QMessageBox.warning(
                    self,
                    "鉴权信息缺失",
                    f"当前 Provider 为【{provider}】，请先在鉴权设置中填写 API Key。",
                )
                return
            if not setting.base_url.strip():
                QMessageBox.warning(self, "配置缺失", "Base URL 不能为空。")
                return
        if not self.config.codex.project_path.strip():
            QMessageBox.warning(self, "校验失败", "项目目录不存在或不是有效目录。")
            return
        if launch_target != "desktop":
            ok, message = self.codex_proxy_group.validate()
            if not ok:
                _show_info_dialog(self, "代理配置不完整", message)
                return
            if codex_has_only_socks5(setting.proxy):
                _show_info_dialog(
                    self,
                    "Codex代理不兼容",
                    "Codex当前不能可靠地仅使用Socks5代理。\n\n"
                    "请启用HTTP或HTTPS代理后再启动。",
                )
                return
            if provider == CODEX_PROVIDER_OFFICIAL and not self._codex_has_proxy():
                if not _show_confirm_dialog(
                    self,
                    "代理提示",
                    "如果不勾选 HTTP 和 HTTPS 代理，有可能导致 Codex 运行异常或闪退。\n"
                    "点击确认继续，无代理启动 Codex。",
                ):
                    return

        target_name = {
            "desktop": "Codex 桌面版",
        }.get(launch_target, "Codex CLI")
        self.codex_status_label.setText(f"正在启动 {target_name} ...")
        self.codex_log_console.append_entry("SYSTEM", f"正在启动 {target_name} ...")
        self._lock_codex_ui()
        self.codex_worker = CodexWorker(
            provider=provider,
            settings=setting,
            project_path=self.config.codex.project_path,
            process_manager=self.codex_process_manager,
            launch_target=launch_target,
            desktop_executable=desktop_executable,
        )
        self._connect_codex_worker()
        self.codex_worker.start()

    def upgrade_codex(self) -> None:
        self._auto_save()
        if self.codex_process_manager.running:
            QMessageBox.information(self, "提示", "Codex 正在运行，请先停止后再升级。")
            return
        desktop_executable = self.codex_service.resolve_desktop_executable()
        if self.codex_service.is_desktop_running(desktop_executable):
            QMessageBox.information(
                self,
                "提示",
                "检测到 Codex 桌面版已在运行，请先关闭后再升级 Codex CLI。",
            )
            return
        provider = self.config.codex.provider
        setting = self.config.codex.provider_settings[provider]
        ok, message = self.codex_proxy_group.validate()
        if not ok:
            _show_info_dialog(self, "代理配置不完整", message)
            return
        if codex_has_only_socks5(setting.proxy):
            _show_info_dialog(
                self,
                "Codex代理不兼容",
                "Codex当前不能可靠地仅使用Socks5代理。\n\n"
                "请启用HTTP或HTTPS代理后再升级。",
            )
            return
        self.codex_status_label.setText("正在升级 Codex CLI ...")
        self.codex_log_console.append_entry("SYSTEM", "正在升级 Codex CLI ...")
        self._lock_codex_ui()
        self.codex_worker = CodexWorker(
            provider=provider,
            settings=setting,
            project_path=self.config.codex.project_path,
            process_manager=self.codex_process_manager,
            upgrade_only=True,
        )
        self._connect_codex_worker()
        self.codex_worker.start()

    def _connect_codex_worker(self) -> None:
        if self.codex_worker is None:
            return
        self.codex_worker.log_signal.connect(self.codex_log_console.append_process_output)
        self.codex_worker.status_signal.connect(self._update_codex_status)
        self.codex_worker.error_signal.connect(self._on_codex_error)
        self.codex_worker.finished_signal.connect(self._on_codex_finished)
        self.codex_worker.npm_not_found_signal.connect(self._on_codex_npm_not_found)
        self.codex_worker.install_success_signal.connect(self._on_codex_install_success)

    def _codex_has_proxy(self) -> bool:
        return any(
            row.enabled.isChecked() and row.host.text().strip()
            for row in (
                self.codex_proxy_group.http,
                self.codex_proxy_group.https,
                self.codex_proxy_group.socks5,
            )
        )

    def _lock_codex_ui(self) -> None:
        self.codex_start_btn.setEnabled(False)
        self.codex_reset_btn.setEnabled(False)
        self.codex_stop_btn.setEnabled(True)
        self.codex_parameter_group.set_ui_enabled(False)
        self.codex_proxy_group.set_ui_enabled(False)

    def _unlock_codex_ui(self) -> None:
        self.codex_reset_btn.setEnabled(True)
        self.codex_stop_btn.setEnabled(False)
        self.codex_parameter_group.set_ui_enabled(True)
        self._sync_codex_target_state()

    def _update_codex_status(self, text: str) -> None:
        self.codex_status_label.setText(text)
        self.codex_log_console.append_entry("SYSTEM", text)

    def _on_codex_error(self, text: str) -> None:
        self.codex_status_label.setText("操作失败")
        self.codex_log_console.append_entry("ERROR", text)
        QMessageBox.critical(self, "Codex 操作失败", text)
        self._unlock_codex_ui()
        self.codex_process_manager.clear()

    def _on_codex_finished(self, return_code: int) -> None:
        if self.codex_worker is not None and self.codex_worker.upgrade_only:
            if self.codex_worker.already_latest:
                message = "Codex CLI 已是最新版本，无须升级。"
                self.codex_status_label.setText(message)
                _show_info_dialog(self, "无需升级", message)
            else:
                self.codex_status_label.setText("Codex CLI 升级流程结束。")
        else:
            target_name = (
                {
                    "desktop": "Codex 桌面版",
                    "vscode": "VS Code",
                }.get(self.codex_worker.launch_target, "Codex CLI")
                if self.codex_worker is not None
                else "Codex CLI"
            )
            self.codex_status_label.setText(
                f"{target_name} 已退出，返回码：{return_code}"
            )
        self._unlock_codex_ui()
        self.codex_process_manager.clear()

    def _on_codex_npm_not_found(self, download_url: str) -> None:
        self._unlock_codex_ui()
        _show_info_dialog(
            self,
            "未安装 Node.js",
            "当前系统尚未安装 Node.js，请先安装后再运行本程序。",
        )
        webbrowser.open(download_url, new=2)

    def _on_codex_install_success(self) -> None:
        self._unlock_codex_ui()
        self.codex_status_label.setText("Codex CLI 已成功安装。")
        self.codex_log_console.append_entry("SYSTEM", "Codex CLI 已成功安装。")
        _show_info_dialog(
            self,
            "安装成功",
            "Codex CLI 已成功安装，请重启本软件后使用。\n\n"
            "点击确认后，本软件将自动关闭。",
        )
        QApplication.instance().quit()

    # ------------------------------------------------------------------
    # 升级 Claude Code（独立按钮）
    # ------------------------------------------------------------------

    def upgrade_claude(self) -> None:
        """点击「升级Claude Code」按钮：在后台线程中升级 Claude Code。"""
        self._auto_save()
        if self.process_manager.running:
            QMessageBox.information(self, "提示", "Claude Code 正在运行，请先停止后再升级。")
            return
        if not self._validate_proxy_config():
            return

        self.status_label.setText("正在升级 Claude Code ...")
        self.log_console.append_entry("SYSTEM", "正在升级 Claude Code ...")

        # ── 锁定 UI ──────────────────────────────────────────────
        self._lock_claude_ui()

        self.worker = ClaudeWorker(self.config, self.process_manager, upgrade_only=True)
        self.worker.log_signal.connect(self.log_console.append_process_output)
        self.worker.status_signal.connect(self._update_status)
        self.worker.error_signal.connect(self._on_worker_error)
        self.worker.finished_signal.connect(self._on_worker_finished)
        self.worker.start()

    # ------------------------------------------------------------------
    # 信号处理
    # ------------------------------------------------------------------

    def _on_install_progress(self, value: int, label: str) -> None:
        """更新安装进度条。"""
        if value > 0:
            self.install_progress_bar.setVisible(True)
            self.install_progress_bar.setValue(value)
            if label:
                self.install_progress_label.setText(label)
                self.install_progress_label.setVisible(True)
        else:
            # value == 0 表示重置/隐藏
            self.install_progress_bar.setVisible(False)
            self.install_progress_bar.setValue(0)
            self.install_progress_label.setVisible(False)
            self.install_progress_label.setText("")

    def _on_npm_not_found(self, download_url: str) -> None:
        """npm 未安装：弹窗提示，用户确认后打开浏览器并退出。"""
        self._unlock_ui()
        self.install_progress_bar.setVisible(False)
        self.install_progress_label.setVisible(False)

        _show_info_dialog(
            self,
            "未安装 Node.js",
            "当前系统尚未安装 Node.js，请先下载安装 Node.js，再运行本程序。\n\n"
            "点击确认后将自动打开 Node.js 下载页面，然后退出程序。",
        )
        webbrowser.open(download_url, new=2)
        QApplication.instance().quit()

    def _on_install_success(self) -> None:
        """Claude Code 安装完成：弹窗提示，用户确认后退出程序。"""
        self._unlock_ui()
        self.install_progress_bar.setVisible(False)
        self.install_progress_label.setVisible(False)

        _show_info_dialog(
            self,
            "安装成功",
            "Claude Code 已成功安装，请退出重启本程序。",
        )
        QApplication.instance().quit()

    def _update_status(self, text: str) -> None:
        self.status_label.setText(text)
        self.log_console.append_entry("SYSTEM", text)

    def _on_worker_error(self, text: str) -> None:
        self.status_label.setText("操作失败")
        self.log_console.append_entry("ERROR", text)
        self.install_progress_bar.setVisible(False)
        self.install_progress_label.setVisible(False)
        QMessageBox.critical(self, "操作失败", text)
        self._unlock_ui()
        self.process_manager.clear()

    def _on_worker_finished(self, return_code: int) -> None:
        # 根据 worker 模式显示不同的状态信息
        if self.worker is not None and self.worker.upgrade_only:
            if self.worker.already_latest:
                message = "Claude Code 已是最新版本，无须升级。"
                self.status_label.setText(message)
                _show_info_dialog(self, "无需升级", message)
            else:
                self.status_label.setText("Claude Code 升级流程结束。")
        else:
            target_name = "Claude Code CLI"
            self.status_label.setText(f"{target_name} 已退出，返回码：{return_code}")
        self.install_progress_bar.setVisible(False)
        self.install_progress_label.setVisible(False)
        self._unlock_ui()
        self.process_manager.clear()

    # ------------------------------------------------------------------
    # 停止
    # ------------------------------------------------------------------

    def stop_claude(self) -> None:
        if self.worker:
            self.worker.request_soft_stop()

    def stop_codex(self) -> None:
        if self.codex_worker:
            self.codex_worker.request_soft_stop()

    def _unlock_ui(self) -> None:
        self.reset_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.parameter_group.set_ui_enabled(True)
        self._sync_claude_target_state()

    def _lock_claude_ui(self) -> None:
        self.start_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.parameter_group.set_ui_enabled(False)
        self.proxy_group.set_ui_enabled(False)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.process_manager.running or self.codex_process_manager.running:
            # 使用自定义弹窗，避免全局 QPushButton { color: white } 导致系统弹窗按钮文字白色不可见
            if not _ask_force_quit(self):
                event.ignore()
                return
            if self.worker:
                self.worker.request_hard_stop()
                self.worker.wait(5000)
            if self.codex_worker:
                self.codex_worker.request_hard_stop()
                self.codex_worker.wait(5000)

        self._auto_save()
        event.accept()


def run_app() -> None:
    import sys

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
