# 路径: src/services/codex_service.py
# 作用: Codex CLI 的检测、安装、升级、启动命令与环境构建

from __future__ import annotations

import os
import json
import shutil
import subprocess
from pathlib import Path

import psutil

from src.core.config_manager import ProxyConfig
from src.services.proxy_service import PROXY_ENV_KEYS, apply_proxy_env
from src.services.validator_service import validate_project_path


_NPM_REGISTRY = "https://registry.npmmirror.com"
CODEX_STORE_SEARCH_URI = "ms-windows-store://search/?query=Codex"


class CodexService:
    def __init__(self) -> None:
        self.executable = "codex"
        self.install_package = "@openai/codex"
        self.node_download_url = "https://nodejs.org/en/download"
        self._resolved: str | None = None

    def check_npm_installed(self) -> bool:
        return shutil.which("npm") is not None

    def resolve_executable(self) -> str | None:
        if self._resolved:
            return self._resolved
        candidate = shutil.which(self.executable)
        if candidate:
            self._resolved = candidate
            return candidate
        if os.name == "nt":
            for base_key in ("APPDATA", "LOCALAPPDATA"):
                base = os.environ.get(base_key)
                if not base:
                    continue
                for name in ("codex.cmd", "codex.exe", "codex.bat"):
                    path = Path(base) / "npm" / name
                    if path.exists():
                        self._resolved = str(path)
                        return self._resolved
        return None

    def check_installed(self) -> bool:
        return self.resolve_executable() is not None

    def resolve_desktop_executable(self) -> Path | None:
        if os.name != "nt":
            return None
        powershell = shutil.which("powershell") or shutil.which("powershell.exe")
        if not powershell:
            return None
        command = [
            powershell,
            "-NoLogo",
            "-NoProfile",
            "-Command",
            (
                "(Get-AppxPackage -Name OpenAI.Codex | "
                "Select-Object -First 1 -ExpandProperty InstallLocation)"
            ),
        ]
        try:
            result = self._run_hidden(command)
        except OSError:
            return None
        if result.returncode != 0:
            return None
        install_location = result.stdout.strip()
        if not install_location:
            return None
        executable = Path(install_location) / "app" / "Codex.exe"
        return executable if executable.is_file() else None

    def is_desktop_running(self, executable: Path | None = None) -> bool:
        target = executable or self.resolve_desktop_executable()
        if target is None:
            return False
        normalized_target = str(target.resolve()).casefold()
        for process in psutil.process_iter(["exe"]):
            try:
                process_executable = process.info.get("exe")
                if (
                    process_executable
                    and str(Path(process_executable).resolve()).casefold()
                    == normalized_target
                ):
                    return True
            except (OSError, psutil.Error):
                continue
        return False

    def stop_desktop(self, executable: Path) -> None:
        normalized_target = str(executable.resolve()).casefold()
        for process in psutil.process_iter(["exe"]):
            try:
                process_executable = process.info.get("exe")
                if (
                    process_executable
                    and str(Path(process_executable).resolve()).casefold()
                    == normalized_target
                ):
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        process.kill()
            except (OSError, psutil.Error):
                continue

    @staticmethod
    def is_any_desktop_running() -> bool:
        for process in psutil.process_iter(["name", "exe"]):
            try:
                name = str(process.info.get("name") or "").casefold()
                executable = str(process.info.get("exe") or "").replace("/", "\\").casefold()
                if name == "codex.exe" and "\\openai.codex_" in executable:
                    return True
            except (OSError, psutil.Error):
                continue
        return False

    @staticmethod
    def is_vscode_extension_running() -> bool:
        for process in psutil.process_iter(["name", "exe", "cmdline"]):
            try:
                command_line = " ".join(
                    str(part) for part in (process.info.get("cmdline") or [])
                )
                process_text = " ".join(
                    (str(process.info.get("exe") or ""), command_line)
                ).replace("/", "\\").casefold()
                marker = "\\.vscode\\extensions\\openai.chatgpt-"
                if (
                    marker in process_text
                    and "\\bin\\" in process_text
                    and "\\codex.exe" in process_text
                ):
                    return True
            except (OSError, psutil.Error):
                continue
        return False

    def build_command(self) -> list[str]:
        resolved = self.resolve_executable()
        if os.name == "nt":
            if resolved and Path(resolved).suffix.lower() in {".cmd", ".bat"}:
                return ["cmd.exe", "/d", "/c", resolved]
            return [resolved or "codex"]
        return [resolved or "codex"]

    def build_install_command(self, upgrade: bool = False) -> list[str]:
        action = "update" if upgrade else "install"
        args = [
            "npm",
            action,
            "-g",
            self.install_package,
            f"--registry={_NPM_REGISTRY}",
        ]
        if os.name != "nt":
            return args
        command_text = " ".join(args)
        powershell = shutil.which("powershell") or shutil.which("powershell.exe")
        if powershell:
            return [
                powershell,
                "-NoLogo",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command_text,
            ]
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", command_text]

    def install(
        self,
        proxy: ProxyConfig | None = None,
    ) -> subprocess.CompletedProcess[str]:
        result = self._run_hidden(
            self.build_install_command(),
            env=self.build_proxy_process_env(proxy or ProxyConfig()),
        )
        self._resolved = None
        return result

    def build_upgrade_command(self) -> list[str]:
        return self.build_install_command(upgrade=True)

    def get_installed_package_version(
        self,
        proxy: ProxyConfig | None = None,
    ) -> str | None:
        return self._get_npm_package_version(installed=True, proxy=proxy)

    def get_latest_package_version(
        self,
        proxy: ProxyConfig | None = None,
    ) -> str | None:
        return self._get_npm_package_version(installed=False, proxy=proxy)

    def _get_npm_package_version(
        self,
        installed: bool,
        proxy: ProxyConfig | None = None,
    ) -> str | None:
        npm_args = (
            ["npm", "list", "-g", self.install_package, "--depth=0", "--json"]
            if installed
            else [
                "npm",
                "view",
                self.install_package,
                "version",
                "--json",
                f"--registry={_NPM_REGISTRY}",
            ]
        )
        command = npm_args
        if os.name == "nt":
            comspec = os.environ.get("COMSPEC") or shutil.which("cmd") or "cmd.exe"
            command = [comspec, "/d", "/c", *npm_args]
        try:
            result = self._run_hidden(
                command,
                env=self.build_proxy_process_env(proxy or ProxyConfig()),
            )
        except OSError:
            return None
        if result.returncode != 0:
            return None
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return None
        if installed:
            package = (data.get("dependencies") or {}).get(self.install_package) or {}
            version = package.get("version")
        else:
            version = data
        return str(version).strip() if version else None

    @staticmethod
    def _run_hidden(
        command: list[str],
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        kwargs: dict[str, object] = {
            "check": False,
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
        }
        if env is not None:
            kwargs["env"] = env
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        return subprocess.run(command, **kwargs)

    @staticmethod
    def build_proxy_process_env(proxy: ProxyConfig) -> dict[str, str]:
        env = os.environ.copy()
        apply_proxy_env(env, proxy, for_codex=True)
        return env

    def build_startup_context(
        self,
        project_path: str,
        proxy: ProxyConfig,
    ) -> tuple[Path, dict[str, str], list[str]]:
        cwd = validate_project_path(project_path)
        env = os.environ.copy()
        apply_proxy_env(env, proxy, for_codex=True)
        resolved = self.resolve_executable()
        if resolved:
            executable_dir = str(Path(resolved).resolve().parent)
            current_path = env.get("PATH", "")
            if executable_dir not in current_path.split(os.pathsep):
                env["PATH"] = executable_dir + os.pathsep + current_path
        return cwd, env, self.build_command()

    def build_desktop_startup_context(
        self,
        executable: Path,
        project_path: str,
    ) -> tuple[Path, dict[str, str], Path]:
        cwd = validate_project_path(project_path)
        env = os.environ.copy()
        for key in PROXY_ENV_KEYS:
            env.pop(key, None)
        return cwd, env, executable
