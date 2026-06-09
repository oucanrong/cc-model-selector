from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.core.config_manager import ProxyConfig, ProxyItem
from src.services.claude_service import ClaudeService


class ClaudeServiceTests(unittest.TestCase):
    def test_native_process_detection_includes_extension_binary(self) -> None:
        processes = [
            SimpleNamespace(info={"name": "Code.exe"}),
            SimpleNamespace(info={"name": "claude.exe"}),
        ]
        with patch(
            "src.services.claude_service.psutil.process_iter",
            return_value=processes,
        ):
            self.assertTrue(ClaudeService.is_any_native_running())

    def test_vscode_extension_process_is_detected_from_dynamic_path(self) -> None:
        processes = [
            SimpleNamespace(
                info={
                    "name": "claude.exe",
                    "exe": (
                        r"D:\Users\someone\.vscode\extensions"
                        r"\anthropic.claude-code-9.9.9-win32-x64"
                        r"\resources\native-binary\claude.exe"
                    ),
                }
            ),
        ]
        with patch(
            "src.services.claude_service.psutil.process_iter",
            return_value=processes,
        ):
            self.assertTrue(ClaudeService.is_vscode_extension_running())

    def test_cli_process_is_not_treated_as_vscode_extension(self) -> None:
        processes = [
            SimpleNamespace(
                info={
                    "name": "claude.exe",
                    "exe": r"C:\Users\someone\AppData\Roaming\npm\claude.exe",
                }
            ),
        ]
        with patch(
            "src.services.claude_service.psutil.process_iter",
            return_value=processes,
        ):
            self.assertFalse(ClaudeService.is_vscode_extension_running())

    def test_vscode_extension_is_detected_from_wrapper_command_line(self) -> None:
        processes = [
            SimpleNamespace(
                info={
                    "name": "Code.exe",
                    "exe": (
                        r"C:\Users\someone\AppData\Local\Programs"
                        r"\Microsoft VS Code\Code.exe"
                    ),
                    "cmdline": [
                        r"C:\Users\someone\AppData\Local\Programs"
                        r"\Microsoft VS Code\Code.exe",
                        r"C:\Users\someone\.vscode\extensions"
                        r"\anthropic.claude-code-2.1.169-win32-x64"
                        r"\resources\native-binary\claude.exe",
                    ],
                }
            ),
        ]
        with patch(
            "src.services.claude_service.psutil.process_iter",
            return_value=processes,
        ):
            self.assertTrue(ClaudeService.is_vscode_extension_running())

    def test_plain_vscode_process_is_not_treated_as_extension(self) -> None:
        processes = [
            SimpleNamespace(
                info={
                    "name": "Code.exe",
                    "exe": (
                        r"C:\Users\someone\AppData\Local\Programs"
                        r"\Microsoft VS Code\Code.exe"
                    ),
                    "cmdline": [
                        r"C:\Users\someone\AppData\Local\Programs"
                        r"\Microsoft VS Code\Code.exe",
                    ],
                }
            ),
        ]
        with patch(
            "src.services.claude_service.psutil.process_iter",
            return_value=processes,
        ):
            self.assertFalse(ClaudeService.is_vscode_extension_running())

    def test_npm_install_receives_selected_proxy_environment(self) -> None:
        service = ClaudeService()
        proxy = ProxyConfig(
            http=ProxyItem(
                enabled=True,
                host="127.0.0.1",
                port="8090",
            ),
        )
        with (
            patch.object(service, "build_install_command", return_value=["npm"]),
            patch(
                "src.services.claude_service.subprocess.run",
            ) as run,
        ):
            service.install_claude_code(proxy)

        env = run.call_args.kwargs["env"]
        self.assertEqual(env["HTTP_PROXY"], "http://127.0.0.1:8090")
        self.assertEqual(env["http_proxy"], "http://127.0.0.1:8090")


if __name__ == "__main__":
    unittest.main()
