from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.config_manager import CodexProviderSettings, ProxyConfig, ProxyItem
from src.core.constants import CODEX_API_KEY_ENV
from src.workers.codex_worker import CodexWorker


class CodexWorkerTests(unittest.TestCase):
    def _worker(self, provider: str) -> tuple[CodexWorker, MagicMock]:
        process_manager = MagicMock()
        process_manager.start.return_value.wait.return_value = 0
        settings = CodexProviderSettings(
            base_url="https://provider.example/v1",
            token="test-api-key",
            model="qwen3.7-max" if provider == "阿里千问" else "mimo-v2.5-pro",
            reasoning_effort="medium",
            thinking_enabled=False,
            proxy=ProxyConfig(),
        )
        worker = CodexWorker(
            provider=provider,
            settings=settings,
            project_path=".",
            process_manager=process_manager,
        )
        worker._ensure_ready = MagicMock(return_value=True)
        worker.service = MagicMock()
        worker.service.build_startup_context.return_value = (
            Path("."),
            {"PATH": "test"},
            ["codex"],
        )
        worker.config_service = MagicMock()
        return worker, process_manager

    def test_direct_provider_skips_router_and_exports_api_key(self) -> None:
        worker, process_manager = self._worker("阿里千问")
        with (
            patch("src.workers.codex_worker.CodexProxyServer") as router,
            patch(
                "src.workers.codex_worker.time.monotonic",
                side_effect=[0, 3],
            ),
        ):
            worker._run_launch()
        router.assert_not_called()
        worker.config_service.activate.assert_called_once()
        call = worker.config_service.activate.call_args.kwargs
        self.assertEqual(call["provider_id"], "qwen")
        self.assertEqual(call["env_key"], CODEX_API_KEY_ENV)
        env = process_manager.start.call_args.args[2]
        self.assertEqual(env[CODEX_API_KEY_ENV], "test-api-key")

    def test_chat_provider_starts_random_port_router(self) -> None:
        worker, process_manager = self._worker("小米MiMo")
        with patch("src.workers.codex_worker.CodexProxyServer") as router:
            router.return_value.base_url = "http://127.0.0.1:54321/v1"
            worker._run_launch()
        router.assert_called_once()
        router.return_value.start.assert_called_once()
        router.return_value.stop.assert_called_once()
        self.assertFalse(
            router.call_args.kwargs["capabilities"]["thinking_enabled"],
        )
        call = worker.config_service.activate.call_args.kwargs
        self.assertEqual(call["base_url"], "http://127.0.0.1:54321/v1")
        self.assertNotIn(
            CODEX_API_KEY_ENV,
            process_manager.start.call_args.args[2],
        )

    def test_direct_provider_does_not_receive_thinking_capability(self) -> None:
        worker, _process_manager = self._worker("阿里千问")
        with patch("src.workers.codex_worker.CodexProxyServer") as router:
            worker._run_launch()
        router.assert_not_called()

    def test_desktop_provider_uses_gui_process_without_proxy_environment(self) -> None:
        worker, process_manager = self._worker("阿里千问")
        executable = Path(r"C:\Program Files\WindowsApps\OpenAI.Codex\app\Codex.exe")
        worker.launch_target = "desktop"
        worker.desktop_executable = executable
        worker.service.build_desktop_startup_context.return_value = (
            Path("."),
            {"PATH": "test"},
            executable,
        )
        worker.service.is_desktop_running.return_value = False
        process_manager.start_gui.return_value.wait.return_value = 0
        with patch("src.workers.codex_worker.CodexProxyServer") as router:
            worker._run_launch()
        router.assert_not_called()
        worker._ensure_ready.assert_not_called()
        process_manager.start.assert_not_called()
        process_manager.start_gui.assert_called_once()
        env = process_manager.start_gui.call_args.args[2]
        self.assertEqual(env[CODEX_API_KEY_ENV], "test-api-key")
        self.assertNotIn("HTTP_PROXY", env)
        self.assertNotIn("HTTPS_PROXY", env)
        self.assertNotIn("ALL_PROXY", env)
        worker.service.build_desktop_startup_context.assert_called_once_with(
            executable,
            ".",
        )

    def test_desktop_ignores_only_socks5_proxy(self) -> None:
        worker, process_manager = self._worker("阿里千问")
        executable = Path(r"C:\Apps\Codex.exe")
        worker.launch_target = "desktop"
        worker.desktop_executable = executable
        worker.settings.proxy = ProxyConfig(
            socks5=ProxyItem(enabled=True, host="127.0.0.1", port="8090"),
        )
        worker.service.build_desktop_startup_context.return_value = (
            Path("."),
            {},
            executable,
        )
        worker.service.is_desktop_running.return_value = False
        process_manager.start_gui.return_value.wait.return_value = 0

        worker._run_launch()

        process_manager.start_gui.assert_called_once()

    def test_vscode_provider_uses_gui_process_and_restores_config(self) -> None:
        worker, process_manager = self._worker("阿里千问")
        executable = Path(r"C:\Apps\Microsoft VS Code\Code.exe")
        worker.launch_target = "vscode"
        worker.vscode_executable = executable
        worker.vscode_service = MagicMock()
        worker.vscode_service.build_startup_context.return_value = (
            Path("."),
            {"HTTP_PROXY": "http://127.0.0.1:8090"},
            [str(executable), "."],
        )
        worker.vscode_service.is_running.return_value = False
        process_manager.start_gui.return_value.poll.return_value = 0

        with patch("src.workers.codex_worker.CodexProxyServer") as router:
            worker._run_launch()

        router.assert_not_called()
        process_manager.start_gui.assert_called_once()
        env = process_manager.start_gui.call_args.args[2]
        self.assertEqual(env[CODEX_API_KEY_ENV], "test-api-key")
        worker.config_service.restore.assert_called_once()

    def test_vscode_chat_provider_keeps_random_port_router(self) -> None:
        worker, process_manager = self._worker("小米MiMo")
        executable = Path(r"C:\Apps\Microsoft VS Code\Code.exe")
        worker.launch_target = "vscode"
        worker.vscode_executable = executable
        worker.vscode_service = MagicMock()
        worker.vscode_service.build_startup_context.return_value = (
            Path("."),
            {},
            [str(executable), "."],
        )
        worker.vscode_service.is_running.return_value = False
        process_manager.start_gui.return_value.poll.return_value = 0

        with (
            patch("src.workers.codex_worker.CodexProxyServer") as router,
            patch(
                "src.workers.codex_worker.time.monotonic",
                side_effect=[0, 3],
            ),
        ):
            router.return_value.base_url = "http://127.0.0.1:54321/v1"
            worker._run_launch()

        router.assert_called_once()
        router.return_value.start.assert_called_once()
        router.return_value.stop.assert_called_once()
        self.assertEqual(
            worker.config_service.activate.call_args.kwargs["base_url"],
            "http://127.0.0.1:54321/v1",
        )

    def test_only_socks5_proxy_is_rejected_before_launch(self) -> None:
        worker, process_manager = self._worker("阿里千问")
        worker.settings.proxy = ProxyConfig(
            socks5=ProxyItem(enabled=True, host="127.0.0.1", port="8090"),
        )
        errors: list[str] = []
        worker.error_signal.connect(errors.append)

        worker._run_launch()

        self.assertEqual(len(errors), 1)
        self.assertIn("仅使用Socks5代理", errors[0])
        worker._ensure_ready.assert_not_called()
        process_manager.start.assert_not_called()


if __name__ == "__main__":
    unittest.main()
