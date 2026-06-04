# 路径: src/ui/widgets/proxy_group.py
# 作用: 代理设置区域控件
# 校验：勾选某个代理时，至少要同时填入 IP 地址和端口号

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.core.config_manager import AppConfig


class _ProxyRow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.enabled = QCheckBox("启用")
        self.enabled.setMinimumHeight(30)

        self.host = QLineEdit()
        self.host.setPlaceholderText("IP地址")
        self.host.setToolTip("IP地址")
        self.host.setMinimumHeight(30)
        self.host.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.port = QLineEdit()
        self.port.setPlaceholderText("端口")
        self.port.setToolTip("端口")
        self.port.setMinimumHeight(30)
        self.port.setMaximumWidth(110)
        self.port.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.username = QLineEdit()
        self.username.setPlaceholderText("用户名")
        self.username.setToolTip("用户名")
        self.username.setMinimumHeight(30)
        self.username.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.password = QLineEdit()
        self.password.setPlaceholderText("密码")
        self.password.setToolTip("密码")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setMinimumHeight(30)
        self.password.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.enabled, 0)
        layout.addWidget(self.host, 2)
        layout.addWidget(self.port, 0)
        layout.addWidget(self.username, 1)
        layout.addWidget(self.password, 1)
        self.setLayout(layout)

        # 勾选代理时，自动填写 127.0.0.1（仅当 IP 为空时）
        self.enabled.toggled.connect(self._on_enabled_toggled)

    def _on_enabled_toggled(self, checked: bool) -> None:
        if checked and not self.host.text().strip():
            self.host.setText("127.0.0.1")

    def set_row_enabled(self, enabled: bool) -> None:
        """启用/禁用该代理行的所有控件（启动时禁用，停止后恢复）。"""
        self.enabled.setEnabled(enabled)
        self.host.setEnabled(enabled)
        self.port.setEnabled(enabled)
        self.username.setEnabled(enabled)
        self.password.setEnabled(enabled)


class ProxyGroup(QGroupBox):
    def __init__(self) -> None:
        super().__init__("设置代理")
        self.http = _ProxyRow()
        self.https = _ProxyRow()
        self.socks5 = _ProxyRow()

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.addRow("HTTP代理", self.http)
        form.addRow("HTTPS代理", self.https)
        form.addRow("Socks5代理", self.socks5)
        self.setLayout(form)

    def set_ui_enabled(self, enabled: bool) -> None:
        """启用/禁用所有代理行控件（启动时禁用，停止后恢复）。"""
        for row in (self.http, self.https, self.socks5):
            row.set_row_enabled(enabled)

    def apply_config(self, config: AppConfig) -> None:
        self._apply_row(self.http, config.proxy.http)
        self._apply_row(self.https, config.proxy.https)
        self._apply_row(self.socks5, config.proxy.socks5)

    def collect_config_data(self) -> dict:
        return {
            "http": self._collect_row(self.http),
            "https": self._collect_row(self.https),
            "socks5": self._collect_row(self.socks5),
        }

    def validate(self) -> tuple[bool, str]:
        """
        校验代理配置：勾选了代理必须同时填写 IP 地址和端口号。
        返回 (True, "") 表示校验通过；
        返回 (False, error_message) 表示校验失败，error_message 说明具体原因。
        """
        checks = [
            (self.http, "HTTP代理"),
            (self.https, "HTTPS代理"),
            (self.socks5, "Socks5代理"),
        ]
        for row, label in checks:
            if not row.enabled.isChecked():
                continue
            host = row.host.text().strip()
            port = row.port.text().strip()
            if not host and not port:
                return (
                    False,
                    f"您已勾选【{label}】，但未填写 IP 地址和端口号。\n\n"
                    "请填写 IP 地址和端口号，或取消勾选该代理后再启动。",
                )
            if not host:
                return (
                    False,
                    f"您已勾选【{label}】，但未填写 IP 地址。\n\n"
                    "请填写 IP 地址后再启动，或取消勾选该代理。",
                )
            if not port:
                return (
                    False,
                    f"您已勾选【{label}】，但未填写端口号。\n\n"
                    "请填写端口号后再启动，或取消勾选该代理。",
                )
        return True, ""

    def _apply_row(self, row: _ProxyRow, data) -> None:
        row.enabled.setChecked(data.enabled)
        row.host.setText(data.host)
        row.port.setText(data.port)

        auth = (data.auth or "").strip()
        if ":" in auth:
            username, password = auth.split(":", 1)
        else:
            username, password = auth, ""
        row.username.setText(username)
        row.password.setText(password)

    def _collect_row(self, row: _ProxyRow) -> dict:
        username = row.username.text().strip()
        password = row.password.text().strip()
        auth = ""
        if username or password:
            auth = f"{username}:{password}"

        return {
            "enabled": row.enabled.isChecked(),
            "host": row.host.text().strip(),
            "port": row.port.text().strip(),
            "auth": auth,
        }
