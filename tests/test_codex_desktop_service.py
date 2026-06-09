from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.core.config_manager import ProxyConfig, ProxyItem
from src.services.codex_service import CodexService


class CodexDesktopServiceTests(unittest.TestCase):
    def test_resolves_store_executable_without_hardcoded_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            install = Path(directory) / "OpenAI.Codex_99.1.2.3_x64"
            executable = install / "app" / "Codex.exe"
            executable.parent.mkdir(parents=True)
            executable.touch()
            result = SimpleNamespace(
                returncode=0,
                stdout=str(install),
                stderr="",
            )
            service = CodexService()
            with (
                patch("src.services.codex_service.os.name", "nt"),
                patch("src.services.codex_service.shutil.which", return_value="powershell.exe"),
                patch.object(service, "_run_hidden", return_value=result),
            ):
                self.assertEqual(service.resolve_desktop_executable(), executable)

    def test_running_detection_matches_resolved_executable(self) -> None:
        executable = Path(r"C:\Apps\OpenAI.Codex\app\Codex.exe")
        processes = [
            SimpleNamespace(info={"exe": str(executable)}),
            SimpleNamespace(info={"exe": r"C:\Windows\notepad.exe"}),
        ]
        service = CodexService()
        with patch(
            "src.services.codex_service.psutil.process_iter",
            return_value=processes,
        ):
            self.assertTrue(service.is_desktop_running(executable))

    def test_vscode_extension_process_is_detected_from_dynamic_path(self) -> None:
        processes = [
            SimpleNamespace(
                info={
                    "name": "codex.exe",
                    "exe": (
                        r"D:\Users\someone\.vscode\extensions"
                        r"\openai.chatgpt-99.123.456-win32-x64"
                        r"\bin\windows-arm64\codex.exe"
                    ),
                }
            ),
        ]
        with patch(
            "src.services.codex_service.psutil.process_iter",
            return_value=processes,
        ):
            self.assertTrue(CodexService.is_vscode_extension_running())

    def test_other_codex_executables_are_not_treated_as_vscode_extension(self) -> None:
        processes = [
            SimpleNamespace(
                info={
                    "name": "codex.exe",
                    "exe": r"C:\Users\someone\AppData\Roaming\npm\codex.exe",
                }
            ),
            SimpleNamespace(
                info={
                    "name": "codex.exe",
                    "exe": (
                        r"C:\Program Files\WindowsApps\OpenAI.Codex_1.0_x64"
                        r"\app\Codex.exe"
                    ),
                }
            ),
            SimpleNamespace(
                info={
                    "name": "codex.exe",
                    "exe": (
                        r"C:\Users\someone\.vscode\extensions"
                        r"\another.extension-1.0\bin\windows-x86_64\codex.exe"
                    ),
                }
            ),
        ]
        with patch(
            "src.services.codex_service.psutil.process_iter",
            return_value=processes,
        ):
            self.assertFalse(CodexService.is_vscode_extension_running())

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
                        r"\openai.chatgpt-26.602.71036-win32-x64"
                        r"\bin\windows-x86_64\codex.exe",
                    ],
                }
            ),
        ]
        with patch(
            "src.services.codex_service.psutil.process_iter",
            return_value=processes,
        ):
            self.assertTrue(CodexService.is_vscode_extension_running())

    def test_plain_vscode_process_is_not_treated_as_codex_extension(self) -> None:
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
            "src.services.codex_service.psutil.process_iter",
            return_value=processes,
        ):
            self.assertFalse(CodexService.is_vscode_extension_running())

    def test_desktop_context_does_not_inject_proxy_environment(self) -> None:
        service = CodexService()
        executable = Path(r"C:\Apps\Codex.exe")
        with patch(
            "src.services.codex_service.validate_project_path",
            return_value=Path(r"C:\Work"),
        ), patch.dict(
            "src.services.codex_service.os.environ",
            {
                "HTTP_PROXY": "http://127.0.0.1:8080",
                "HTTPS_PROXY": "http://127.0.0.1:8080",
                "ALL_PROXY": "socks5://127.0.0.1:1080",
                "WS_PROXY": "http://127.0.0.1:8080",
                "WSS_PROXY": "http://127.0.0.1:8080",
                "http_proxy": "http://127.0.0.1:8080",
                "https_proxy": "http://127.0.0.1:8080",
                "all_proxy": "socks5://127.0.0.1:1080",
                "ws_proxy": "http://127.0.0.1:8080",
                "wss_proxy": "http://127.0.0.1:8080",
                "PATH": "test",
            },
            clear=True,
        ):
            _, env, returned_executable = service.build_desktop_startup_context(
                executable,
                r"C:\Work",
            )
        self.assertNotIn("HTTP_PROXY", env)
        self.assertNotIn("HTTPS_PROXY", env)
        self.assertNotIn("ALL_PROXY", env)
        self.assertNotIn("WS_PROXY", env)
        self.assertNotIn("WSS_PROXY", env)
        self.assertNotIn("http_proxy", env)
        self.assertNotIn("https_proxy", env)
        self.assertNotIn("all_proxy", env)
        self.assertNotIn("ws_proxy", env)
        self.assertNotIn("wss_proxy", env)
        self.assertEqual(env["PATH"], "test")
        self.assertEqual(returned_executable, executable)

    def test_stop_desktop_terminates_matching_process_only(self) -> None:
        executable = Path(r"C:\Apps\OpenAI.Codex\app\Codex.exe")
        matching = SimpleNamespace(
            info={"exe": str(executable)},
            terminate=MagicMock(),
            wait=MagicMock(),
            kill=MagicMock(),
        )
        other = SimpleNamespace(
            info={"exe": r"C:\Windows\notepad.exe"},
            terminate=MagicMock(),
            wait=MagicMock(),
            kill=MagicMock(),
        )
        service = CodexService()
        with patch(
            "src.services.codex_service.psutil.process_iter",
            return_value=[matching, other],
        ):
            service.stop_desktop(executable)
        matching.terminate.assert_called_once()
        matching.wait.assert_called_once_with(timeout=5)
        matching.kill.assert_not_called()
        other.terminate.assert_not_called()

    def test_npm_install_receives_selected_proxy_environment(self) -> None:
        service = CodexService()
        proxy = ProxyConfig(
            https=ProxyItem(
                enabled=True,
                host="127.0.0.1",
                port="8090",
            ),
        )
        with (
            patch.object(service, "build_install_command", return_value=["npm"]),
            patch.object(service, "_run_hidden") as run,
        ):
            service.install(proxy)

        env = run.call_args.kwargs["env"]
        self.assertEqual(env["HTTP_PROXY"], "http://127.0.0.1:8090")
        self.assertEqual(env["HTTPS_PROXY"], "http://127.0.0.1:8090")


if __name__ == "__main__":
    unittest.main()
