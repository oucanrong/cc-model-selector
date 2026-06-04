# 路径: C:\Users\oucan\Documents\vscode\claude_code启动器\src\ui\main_window.py
# 作用: 主窗口与交互逻辑

from __future__ import annotations

import webbrowser

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QCloseEvent, QFont
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
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from src.core.config_manager import AppConfig, ConfigManager, ProxyConfig, ProxyItem, ProviderSettings
from src.core.constants import APP_NAME, PROVIDER_CLAUDE_DEFAULT, PROVIDER_CLAUDE_RELAY
from src.core.logger import setup_logger
from src.core.process_manager import ProcessManager
from src.ui.styles import APP_QSS
from src.ui.widgets.auth_settings_dialog import AuthSettingsDialog
from src.ui.widgets.log_console import LogConsole
from src.ui.widgets.parameter_group import ParameterGroup
from src.ui.widgets.proxy_group import ProxyGroup
from src.workers.claude_worker import ClaudeWorker

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

    msg = QLabel("Claude Code 仍在运行，是否强制停止并退出？")
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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1200, 840)

        self._apply_fonts()

        self.logger = setup_logger()
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load()
        self.process_manager = ProcessManager()
        self.worker: ClaudeWorker | None = None
        self._loading = False

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(250)
        self._autosave_timer.timeout.connect(self._auto_save)

        self._build_ui()
        self._bind_config()
        self._wire_autosave()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)

        header_row = QHBoxLayout()
        header_row.addStretch(1)
        self.auth_btn = QPushButton("鉴权设置")
        self.auth_btn.setObjectName("authSettingsButton")
        self.auth_btn.setMinimumWidth(120)
        self.auth_btn.clicked.connect(self.open_auth_settings)
        header_row.addWidget(self.auth_btn)
        root.addLayout(header_row)

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

        self.start_btn.clicked.connect(self.start_claude)
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
            btn.setMinimumWidth(120)
            button_row.addWidget(btn)

        root.addWidget(self.parameter_group)
        root.addWidget(self.proxy_group)
        root.addWidget(QLabel("日志输出"))
        root.addWidget(self.log_console, 1)
        # 进度条区域
        root.addWidget(self.install_progress_bar)
        root.addWidget(self.install_progress_label)
        root.addWidget(self.status_label)
        root.addLayout(button_row)

        self.setCentralWidget(central)
        self.setStyleSheet(APP_QSS)

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
            self.config.token = self.config.auth_tokens.get(self.config.provider, "").strip()
        finally:
            self._loading = False
        self._refresh_status()

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
        pg.project_path_edit.textChanged.connect(self._schedule_autosave)
        # Kimi / GML5 专用参数
        pg.enable_tool_search.currentTextChanged.connect(self._schedule_autosave)
        pg.disable_nonessential_traffic.currentTextChanged.connect(self._schedule_autosave)
        pg.api_timeout_ms.textChanged.connect(self._schedule_autosave)

        for row in (self.proxy_group.http, self.proxy_group.https, self.proxy_group.socks5):
            row.enabled.toggled.connect(self._schedule_autosave)
            row.host.textChanged.connect(self._schedule_autosave)
            row.port.textChanged.connect(self._schedule_autosave)
            row.username.textChanged.connect(self._schedule_autosave)
            row.password.textChanged.connect(self._schedule_autosave)

    def _refresh_status(self) -> None:
        self.status_label.setText(
            f"Provider: {self.config.provider} | 项目目录: {self.config.project_path or '未选择'}"
        )

    def _schedule_autosave(self) -> None:
        if self._loading:
            return
        self._autosave_timer.start()

    def _handle_provider_change(self, provider: str) -> None:
        # 先把当前 UI 数据存入旧 provider 的 provider_settings
        self._sync_config_from_ui()
        # 刷新旧 provider 到 provider_settings（确保 proxy 等参数持久化）
        self.config_manager._flush_active_provider(self.config)

        # 切换到新 provider
        self.config.provider = provider

        # 从 provider_settings 恢复新 provider 的参数到 UI
        self._loading = True
        try:
            from src.core.config_manager import ConfigManager as _CM
            _CM(self.config_manager.path)._sync_active_provider(self.config)
            self.parameter_group.apply_config(self.config)
            self.proxy_group.apply_config(self.config)
        finally:
            self._loading = False

        self._schedule_autosave()
        self._refresh_status()

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
        self.config.project_path = data["project_path"]
        # Kimi / GML5 专用参数
        self.config.enable_tool_search = data["enable_tool_search"]
        self.config.disable_nonessential_traffic = data["disable_nonessential_traffic"]
        self.config.api_timeout_ms = data["api_timeout_ms"]

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
        self.config_manager.save(self.config)
        self._refresh_status()

    def open_auth_settings(self) -> None:
        dialog = AuthSettingsDialog(self.config.provider_settings, self)
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
            "如果你当前使用其它代理软件并设置了全局代理，无须在本软件中设置代理参数。\n\n"
            "如果你当前使用其它代理软件而没有设置全局代理，使用 Claude 官方接口很可能需要你"
            "设置 http 和 https 代理参数，否则会造成 Claude Code 运行异常或闪退，"
            "点击确认继续启动。"
        )
        return _show_confirm_dialog(self, "代理提示", msg)

    def start_claude(self) -> None:
        self._auto_save()

        if self.process_manager.running:
            QMessageBox.information(self, "提示", "Claude Code 已在运行，禁止重复启动。")
            return

        # ── 校验：第三方 Provider 的 API 鉴权信息不能为空 ──────────────────────
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

        # ── 校验：项目目录不能为空 ──────────────────────────────────────────────
        try:
            validate_path = self.parameter_group.project_path_edit.text().strip()
            if not validate_path:
                raise ValueError("项目目录不存在或不是有效目录。")
        except Exception as exc:
            QMessageBox.warning(self, "校验失败", str(exc))
            return

        # ── 校验：代理配置（勾选必须填 IP + 端口） ────────────────────────────
        if not self._validate_proxy_config():
            return

        # ── Claude官方接口：代理为空时提示确认 ───────────────────────────────
        if self.config.provider == PROVIDER_CLAUDE_DEFAULT:
            if not self._check_proxy_for_official():
                return

        self.status_label.setText("正在启动 Claude Code ...")
        self.log_console.append_entry("SYSTEM", "正在启动 Claude Code ...")

        self.start_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # ── 禁用所有参数输入控件（Provider、模型参数、代理、工作目录） ──────
        self.parameter_group.set_ui_enabled(False)
        self.proxy_group.set_ui_enabled(False)

        self.worker = ClaudeWorker(self.config, self.process_manager)
        self.worker.log_signal.connect(self.log_console.append_process_output)
        self.worker.status_signal.connect(self._update_status)
        self.worker.error_signal.connect(self._on_worker_error)
        self.worker.finished_signal.connect(self._on_worker_finished)
        # 新增信号连接
        self.worker.npm_not_found_signal.connect(self._on_npm_not_found)
        self.worker.install_success_signal.connect(self._on_install_success)
        self.worker.install_progress_signal.connect(self._on_install_progress)
        self.worker.start()

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
        self.status_label.setText("启动失败")
        self.log_console.append_entry("ERROR", text)
        self.install_progress_bar.setVisible(False)
        self.install_progress_label.setVisible(False)
        QMessageBox.critical(self, "启动失败", text)
        self._unlock_ui()
        self.process_manager.clear()

    def _on_worker_finished(self, return_code: int) -> None:
        self.status_label.setText(f"Claude Code 已退出，返回码：{return_code}")
        self.install_progress_bar.setVisible(False)
        self.install_progress_label.setVisible(False)
        self._unlock_ui()
        self.process_manager.clear()

    def stop_claude(self) -> None:
        if self.worker:
            self.worker.request_soft_stop()

    def _unlock_ui(self) -> None:
        self.start_btn.setEnabled(True)
        self.reset_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        # ── 恢复所有参数输入控件 ──────────────────────────────────────────
        self.parameter_group.set_ui_enabled(True)
        self.proxy_group.set_ui_enabled(True)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.process_manager.running:
            # 使用自定义弹窗，避免全局 QPushButton { color: white } 导致系统弹窗按钮文字白色不可见
            if not _ask_force_quit(self):
                event.ignore()
                return
            if self.worker:
                self.worker.request_hard_stop()

        self._auto_save()
        event.accept()


def run_app() -> None:
    import sys

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
