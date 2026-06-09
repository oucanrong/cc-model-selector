from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.ui.widgets.proxy_group import ProxyGroup


class ProxyGroupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_each_proxy_type_requires_ip_and_port(self) -> None:
        group = ProxyGroup()
        for row in (group.http, group.https, group.socks5):
            row.enabled.setChecked(True)
            row.host.clear()
            row.port.clear()
            ok, message = group.validate()
            self.assertFalse(ok)
            self.assertIn("IP 地址和端口号", message)
            row.enabled.setChecked(False)

    def test_each_proxy_type_requires_ip(self) -> None:
        group = ProxyGroup()
        for row in (group.http, group.https, group.socks5):
            row.enabled.setChecked(True)
            row.host.clear()
            row.port.setText("8090")
            ok, message = group.validate()
            self.assertFalse(ok)
            self.assertIn("请填写 IP 地址", message)
            row.enabled.setChecked(False)

    def test_each_proxy_type_uses_requested_missing_port_message(self) -> None:
        group = ProxyGroup()
        for row in (group.http, group.https, group.socks5):
            row.enabled.setChecked(True)
            row.host.setText("127.0.0.1")
            row.port.clear()
            ok, message = group.validate()
            self.assertFalse(ok)
            self.assertEqual(
                message,
                "请填写由其它代理软件定义的端口号。",
            )
            row.enabled.setChecked(False)

    def test_clear_removes_all_proxy_values(self) -> None:
        group = ProxyGroup()
        for row in (group.http, group.https, group.socks5):
            row.enabled.setChecked(True)
            row.host.setText("127.0.0.1")
            row.port.setText("8090")
            row.username.setText("user")
            row.password.setText("password")

        group.clear()

        for row in (group.http, group.https, group.socks5):
            self.assertFalse(row.enabled.isChecked())
            self.assertEqual(row.host.text(), "")
            self.assertEqual(row.port.text(), "")
            self.assertEqual(row.username.text(), "")
            self.assertEqual(row.password.text(), "")


if __name__ == "__main__":
    unittest.main()
