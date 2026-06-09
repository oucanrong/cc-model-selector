# 路径: src/workers/codex_worker.py
# 作用: Codex CLI 启动、升级、本地协议转换和配置恢复线程

from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from src.core.config_manager import CodexProviderSettings, ProxyConfig
from src.core.constants import (
    CODEX_API_KEY_ENV,
    CODEX_PROTOCOL_CHAT_PROXY,
    CODEX_PROTOCOL_RESPONSES_DIRECT,
    CODEX_REASONING_CONTROL_TOGGLE,
    CODEX_PROVIDER_DEFAULTS,
    CODEX_PROVIDER_OFFICIAL,
    get_codex_context_window,
)
from src.core.process_manager import ProcessManager
from src.services.codex_config_service import CodexConfigService
from src.services.codex_proxy_server import CodexProxyServer
from src.services.codex_service import CodexService
from src.services.proxy_service import codex_has_only_socks5
from src.services.vscode_service import VSCodeService


class CodexWorker(QThread):
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)
    npm_not_found_signal = pyqtSignal(str)
    install_success_signal = pyqtSignal()

    def __init__(
        self,
        provider: str,
        settings: CodexProviderSettings,
        project_path: str,
        process_manager: ProcessManager,
        upgrade_only: bool = False,
        launch_target: str = "cli",
        desktop_executable: Path | None = None,
        vscode_executable: Path | None = None,
    ) -> None:
        super().__init__()
        self.provider = provider
        self.settings = settings
        self.project_path = project_path
        self.process_manager = process_manager
        self.upgrade_only = upgrade_only
        self.launch_target = launch_target
        self.desktop_executable = desktop_executable
        self.vscode_executable = vscode_executable
        self.already_latest = False
        self.service = CodexService()
        self.config_service = CodexConfigService()
        self.proxy_server: CodexProxyServer | None = None
        self.vscode_service = VSCodeService()
        self._stop_requested = False
        self._upgrade_proc: subprocess.Popen[str] | None = None

    def run(self) -> None:
        if self.upgrade_only:
            self._run_upgrade()
        else:
            self._run_launch()

    def _ensure_ready(self) -> bool:
        if self.service.check_installed():
            return True
        if not self.service.check_npm_installed():
            self.npm_not_found_signal.emit(self.service.node_download_url)
            return False
        self.status_signal.emit("未检测到 Codex CLI，正在自动安装 ...")
        result = self.service.install(self.settings.proxy)
        self._emit_output("INSTALL", result.stdout)
        self._emit_output("INSTALL-ERR", result.stderr)
        if result.returncode != 0 or not self.service.check_installed():
            raise RuntimeError("Codex CLI 自动安装失败，请检查 npm、网络或权限。")
        self.status_signal.emit("Codex CLI 已成功安装。")
        self.log_signal.emit("[SYSTEM] Codex CLI 已成功安装。")
        self.install_success_signal.emit()
        return False

    def _run_launch(self) -> None:
        try:
            effective_proxy = (
                ProxyConfig()
                if self.launch_target == "desktop"
                else self.settings.proxy
            )
            if codex_has_only_socks5(effective_proxy):
                raise RuntimeError(
                    "Codex当前不能可靠地仅使用Socks5代理。"
                    "请启用HTTP或HTTPS代理后再启动。"
                )
            if self.launch_target == "cli" and not self._ensure_ready():
                return
            defaults = CODEX_PROVIDER_DEFAULTS[self.provider]
            protocol = defaults["protocol"]
            context_window = get_codex_context_window(
                self.provider,
                self.settings.model,
            )
            if protocol == CODEX_PROTOCOL_CHAT_PROXY:
                capabilities = dict(defaults.get("chat_reasoning", {}))
                if (
                    defaults["reasoning_control"]
                    == CODEX_REASONING_CONTROL_TOGGLE
                ):
                    capabilities["thinking_enabled"] = (
                        self.settings.thinking_enabled
                    )
                self.proxy_server = CodexProxyServer(
                    upstream_base_url=self.settings.base_url,
                    api_key=self.settings.token,
                    model=self.settings.model,
                    proxy=effective_proxy,
                    capabilities=capabilities,
                    log=self.log_signal.emit,
                )
                self.proxy_server.start()
                self.config_service.activate(
                    model=self.settings.model,
                    base_url=self.proxy_server.base_url,
                    display_name=str(
                        defaults.get("display_names", {})
                        .get(self.settings.model, self.settings.model)
                    ),
                    context_window=context_window or 128_000,
                    reasoning_effort=self.settings.reasoning_effort,
                )
            elif protocol == CODEX_PROTOCOL_RESPONSES_DIRECT:
                self.config_service.activate(
                    model=self.settings.model,
                    base_url=self.settings.base_url,
                    display_name=str(
                        defaults.get("display_names", {})
                        .get(self.settings.model, self.settings.model)
                    ),
                    context_window=context_window or 0,
                    provider_id=str(defaults["provider_id"]),
                    provider_name=str(defaults["provider_name"]),
                    reasoning_effort=self.settings.reasoning_effort,
                    env_key=CODEX_API_KEY_ENV,
                )

            if self.launch_target == "desktop":
                if self.desktop_executable is None:
                    raise RuntimeError("未找到 Codex 桌面版程序。")
                cwd, env, executable = self.service.build_desktop_startup_context(
                    self.desktop_executable,
                    self.project_path,
                )
                command_text = str(executable)
            elif self.launch_target == "vscode":
                if self.vscode_executable is None:
                    raise RuntimeError("未找到 VS Code 程序。")
                cwd, env, command = self.vscode_service.build_startup_context(
                    self.vscode_executable,
                    self.project_path,
                    self.settings.proxy,
                    for_codex=True,
                )
                command_text = " ".join(command)
            else:
                cwd, env, command = self.service.build_startup_context(
                    self.project_path,
                    self.settings.proxy,
                )
                command_text = " ".join(command)
            if protocol == CODEX_PROTOCOL_RESPONSES_DIRECT:
                env[CODEX_API_KEY_ENV] = self.settings.token
            target_name = {
                "desktop": "Codex 桌面版",
                "vscode": "VS Code",
            }.get(self.launch_target, "Codex CLI")
            self.status_signal.emit(f"正在启动 {target_name}：{cwd}")
            self.log_signal.emit(f"[SYSTEM] 工作目录：{cwd}")
            self.log_signal.emit(f"[SYSTEM] 启动程序：{command_text}")
            if self.launch_target == "desktop":
                proc = self.process_manager.start_gui(executable, cwd, env)
                self.status_signal.emit("Codex 桌面版已启动。")
            elif self.launch_target == "vscode":
                proc = self.process_manager.start_gui(
                    self.vscode_executable,
                    cwd,
                    env,
                    [str(cwd)],
                )
                self.status_signal.emit("VS Code 已启动。")
            else:
                proc = self.process_manager.start(command, cwd, env)
                self.status_signal.emit("Codex CLI 已在独立终端中启动。")
            if self.launch_target == "vscode":
                startup_deadline = time.monotonic() + 2
                while not self._stop_requested:
                    app_running = self.vscode_service.is_running(
                        self.vscode_executable
                    )
                    if (
                        proc.poll() is not None
                        and not app_running
                        and time.monotonic() >= startup_deadline
                    ):
                        break
                    time.sleep(0.5)
                return_code = proc.poll() or 0
            else:
                return_code = proc.wait()
            if self.launch_target == "desktop":
                while (
                    not self._stop_requested
                    and self.service.is_desktop_running(executable)
                ):
                    time.sleep(0.5)
            self.finished_signal.emit(return_code)
        except Exception as exc:
            self.error_signal.emit(str(exc))
        finally:
            self._cleanup()

    def _run_upgrade(self) -> None:
        self.status_signal.emit("正在检查 Codex CLI 更新 ...")
        self.log_signal.emit("[SYSTEM] 正在检查 Codex CLI 更新 ...")
        installed = self.service.get_installed_package_version(self.settings.proxy)
        latest = self.service.get_latest_package_version(self.settings.proxy)
        if installed and latest and installed == latest:
            self.already_latest = True
            message = f"Codex CLI 已是最新版本（{installed}），无须升级。"
            self.status_signal.emit(message)
            self.log_signal.emit(f"[SYSTEM] {message}")
            self.finished_signal.emit(0)
            return
        self.status_signal.emit("正在升级中")
        self.log_signal.emit("[SYSTEM] Codex CLI 正在升级中 ...")
        command = self.service.build_upgrade_command()
        kwargs: dict[str, object] = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "env": self.service.build_proxy_process_env(self.settings.proxy),
        }
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        try:
            self._upgrade_proc = subprocess.Popen(command, **kwargs)

            def read_stream(stream, prefix: str) -> None:
                if stream is None:
                    return
                for line in iter(stream.readline, ""):
                    self._emit_output(prefix, line)

            threads = [
                threading.Thread(
                    target=read_stream,
                    args=(self._upgrade_proc.stdout, "UPGRADE"),
                    daemon=True,
                ),
                threading.Thread(
                    target=read_stream,
                    args=(self._upgrade_proc.stderr, "UPGRADE-ERR"),
                    daemon=True,
                ),
            ]
            for thread in threads:
                thread.start()
            while self._upgrade_proc.poll() is None:
                if self._stop_requested:
                    self._upgrade_proc.terminate()
                    break
                time.sleep(0.1)
            for thread in threads:
                thread.join(timeout=2)
            self.finished_signal.emit(self._upgrade_proc.returncode or 0)
        except Exception as exc:
            self.error_signal.emit(str(exc))
        finally:
            self._upgrade_proc = None

    def _cleanup(self) -> None:
        try:
            self.config_service.restore()
        finally:
            if self.proxy_server is not None:
                self.proxy_server.stop()
                self.proxy_server = None

    def _emit_output(self, prefix: str, value: str | None) -> None:
        for line in (value or "").splitlines():
            if line.strip():
                self.log_signal.emit(f"[{prefix}] {line.rstrip()}")

    def request_soft_stop(self) -> None:
        self._stop_requested = True
        if self._upgrade_proc is not None and self._upgrade_proc.poll() is None:
            self._upgrade_proc.terminate()
        elif self.launch_target == "desktop":
            self.process_manager.stop_gui()
            if self.desktop_executable is not None:
                self.service.stop_desktop(self.desktop_executable)
        elif self.launch_target == "vscode":
            self.process_manager.stop_gui()
            if self.vscode_executable is not None:
                self.vscode_service.stop(self.vscode_executable)
        elif not self.process_manager.stop_soft():
            self.process_manager.stop_hard()

    def request_hard_stop(self) -> None:
        self._stop_requested = True
        if self._upgrade_proc is not None:
            self._upgrade_proc.kill()
        elif self.launch_target == "desktop":
            self.process_manager.stop_hard()
            if self.desktop_executable is not None:
                self.service.stop_desktop(self.desktop_executable)
        elif self.launch_target == "vscode":
            self.process_manager.stop_hard()
            if self.vscode_executable is not None:
                self.vscode_service.stop(self.vscode_executable)
        else:
            self.process_manager.stop_hard()
