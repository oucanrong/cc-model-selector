from __future__ import annotations

import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

from src.core.config_manager import (
    AppConfig,
    CodexProviderSettings,
    ProxyConfig,
    ProxyItem,
)
from src.core.constants import CODEX_PROVIDER_OFFICIAL
from src.core.process_manager import ProcessManager
from src.workers.claude_worker import ClaudeWorker
from src.workers.codex_worker import CodexWorker


class UpgradeCheckTests(unittest.TestCase):
    def test_claude_skips_upgrade_when_already_latest(self) -> None:
        worker = ClaudeWorker(AppConfig(), ProcessManager(), upgrade_only=True)
        with (
            patch.object(
                worker.service,
                "get_installed_package_version",
                return_value="2.1.168",
            ),
            patch.object(
                worker.service,
                "get_latest_package_version",
                return_value="2.1.168",
            ),
            patch.object(worker.service, "build_upgrade_command") as build_command,
        ):
            result = worker._try_upgrade_claude()

        self.assertTrue(result)
        self.assertTrue(worker.already_latest)
        build_command.assert_not_called()

    def test_codex_skips_upgrade_when_already_latest(self) -> None:
        worker = CodexWorker(
            provider=CODEX_PROVIDER_OFFICIAL,
            settings=CodexProviderSettings(),
            project_path="",
            process_manager=ProcessManager(),
            upgrade_only=True,
        )
        with (
            patch.object(
                worker.service,
                "get_installed_package_version",
                return_value="0.137.0",
            ),
            patch.object(
                worker.service,
                "get_latest_package_version",
                return_value="0.137.0",
            ),
            patch.object(worker.service, "build_upgrade_command") as build_command,
        ):
            worker._run_upgrade()

        self.assertTrue(worker.already_latest)
        build_command.assert_not_called()

    def test_claude_upgrade_status_moves_from_checking_to_upgrading(self) -> None:
        worker = ClaudeWorker(AppConfig(), ProcessManager(), upgrade_only=True)
        statuses: list[str] = []
        worker.status_signal.connect(statuses.append)
        process = MagicMock(
            stdout=StringIO(""),
            stderr=StringIO(""),
            returncode=0,
        )
        process.poll.return_value = 0
        with (
            patch.object(
                worker.service,
                "get_installed_package_version",
                return_value="1.0.0",
            ),
            patch.object(
                worker.service,
                "get_latest_package_version",
                return_value="2.0.0",
            ),
            patch.object(
                worker.service,
                "build_upgrade_command",
                return_value=["npm", "update"],
            ),
            patch("src.workers.claude_worker.subprocess.Popen", return_value=process),
        ):
            worker._try_upgrade_claude()

        self.assertEqual(
            statuses,
            [
                "正在检查 Claude Code 更新 ...",
                "正在升级中",
                "Claude Code 升级完成。",
            ],
        )

    def test_codex_upgrade_status_moves_from_checking_to_upgrading(self) -> None:
        worker = CodexWorker(
            provider=CODEX_PROVIDER_OFFICIAL,
            settings=CodexProviderSettings(),
            project_path="",
            process_manager=ProcessManager(),
            upgrade_only=True,
        )
        statuses: list[str] = []
        worker.status_signal.connect(statuses.append)
        process = MagicMock(
            stdout=StringIO(""),
            stderr=StringIO(""),
            returncode=0,
        )
        process.poll.return_value = 0
        with (
            patch.object(
                worker.service,
                "get_installed_package_version",
                return_value="1.0.0",
            ),
            patch.object(
                worker.service,
                "get_latest_package_version",
                return_value="2.0.0",
            ),
            patch.object(
                worker.service,
                "build_upgrade_command",
                return_value=["npm", "update"],
            ),
            patch("src.workers.codex_worker.subprocess.Popen", return_value=process),
        ):
            worker._run_upgrade()

        self.assertEqual(
            statuses,
            [
                "正在检查 Codex CLI 更新 ...",
                "正在升级中",
            ],
        )

    def test_upgrade_processes_receive_selected_proxy_environment(self) -> None:
        proxy = ProxyConfig(
            http=ProxyItem(enabled=True, host="127.0.0.1", port="8090"),
        )
        claude_config = AppConfig(proxy=proxy)
        claude = ClaudeWorker(
            claude_config,
            ProcessManager(),
            upgrade_only=True,
        )
        codex_settings = CodexProviderSettings(proxy=proxy)
        codex = CodexWorker(
            provider=CODEX_PROVIDER_OFFICIAL,
            settings=codex_settings,
            project_path="",
            process_manager=ProcessManager(),
            upgrade_only=True,
        )
        claude_process = MagicMock(
            stdout=StringIO(""),
            stderr=StringIO(""),
            returncode=0,
        )
        claude_process.poll.return_value = 0
        codex_process = MagicMock(
            stdout=StringIO(""),
            stderr=StringIO(""),
            returncode=0,
        )
        codex_process.poll.return_value = 0

        with (
            patch.object(
                claude.service,
                "get_installed_package_version",
                return_value="1",
            ),
            patch.object(
                claude.service,
                "get_latest_package_version",
                return_value="2",
            ),
            patch.object(
                claude.service,
                "build_upgrade_command",
                return_value=["npm", "update"],
            ),
            patch(
                "src.workers.claude_worker.subprocess.Popen",
                return_value=claude_process,
            ) as claude_popen,
        ):
            claude._try_upgrade_claude()

        with (
            patch.object(
                codex.service,
                "get_installed_package_version",
                return_value="1",
            ),
            patch.object(
                codex.service,
                "get_latest_package_version",
                return_value="2",
            ),
            patch.object(
                codex.service,
                "build_upgrade_command",
                return_value=["npm", "update"],
            ),
            patch(
                "src.workers.codex_worker.subprocess.Popen",
                return_value=codex_process,
            ) as codex_popen,
        ):
            codex._run_upgrade()

        self.assertEqual(
            claude_popen.call_args.kwargs["env"]["HTTP_PROXY"],
            "http://127.0.0.1:8090",
        )
        self.assertEqual(
            codex_popen.call_args.kwargs["env"]["HTTP_PROXY"],
            "http://127.0.0.1:8090",
        )


if __name__ == "__main__":
    unittest.main()
