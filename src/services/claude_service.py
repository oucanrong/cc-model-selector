# 路径: C:\Users\oucan\Documents\vscode\claude_code启动器\src\services\claude_service.py
# 作用: Claude Code 启动命令、安装、升级与上下文构建（修复 Windows 下 claude 命令误判）

from __future__ import annotations

import os
import json
import shutil
import subprocess
import webbrowser
from pathlib import Path

import psutil

from src.core.config_manager import AppConfig, ProxyConfig
from .env_builder_service import build_env
from .proxy_service import apply_proxy_env
from .validator_service import validate_project_path

# 淘宝 npm 镜像源
_NPM_REGISTRY = "https://registry.npmmirror.com"


class ClaudeService:
    def __init__(self) -> None:
        self.executable = "claude"
        self.install_package = "@anthropic-ai/claude-code"
        self.node_download_url = "https://nodejs.org/en/download"
        self._resolved_claude_executable: str | None = None

    def check_claude_installed(self) -> bool:
        return self.resolve_claude_executable() is not None

    def check_npm_installed(self) -> bool:
        return shutil.which("npm") is not None

    def open_node_download_page(self) -> None:
        webbrowser.open(self.node_download_url, new=2)

    def _dedupe_paths(self, paths: list[Path]) -> list[Path]:
        result: list[Path] = []
        seen: set[str] = set()
        for path in paths:
            key = str(path.expanduser().resolve(strict=False)).lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(path.expanduser())
        return result

    def _get_npm_prefixes(self) -> list[Path]:
        prefixes: list[Path] = []

        env_prefix = os.environ.get("NPM_CONFIG_PREFIX", "").strip()
        if env_prefix:
            prefixes.append(Path(env_prefix))

        if os.name == "nt":
            for key in ("APPDATA", "LOCALAPPDATA"):
                base = os.environ.get(key, "").strip()
                if base:
                    prefixes.append(Path(base) / "npm")
        else:
            prefixes.extend(
                [
                    Path.home() / ".npm-global",
                    Path.home() / ".local" / "bin",
                ]
            )

        if self.check_npm_installed():
            for command in (["npm", "prefix", "-g"], ["npm", "config", "get", "prefix"]):
                try:
                    completed = subprocess.run(
                        command,
                        check=False,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                    )
                except Exception:
                    continue

                prefix_text = completed.stdout.strip()
                if completed.returncode == 0 and prefix_text:
                    prefixes.append(Path(prefix_text))

        return self._dedupe_paths(prefixes)

    def _iter_candidate_executables(self) -> list[Path]:
        candidates: list[Path] = []

        def add(path: Path) -> None:
            candidates.append(path)

        which_path = shutil.which(self.executable)
        if which_path:
            add(Path(which_path))

        npm_prefixes = self._get_npm_prefixes()
        if os.name == "nt":
            executable_names = ("claude.cmd", "claude.exe", "claude.bat", "claude")
            for prefix in npm_prefixes:
                for name in executable_names:
                    add(prefix / name)
                add(prefix / "bin" / "claude.cmd")
                add(prefix / "bin" / "claude.exe")
                add(prefix / "bin" / "claude.bat")
        else:
            for prefix in npm_prefixes:
                add(prefix / self.executable)
                add(prefix / "bin" / self.executable)

        return self._dedupe_paths(candidates)

    def resolve_claude_executable(self) -> str | None:
        if self._resolved_claude_executable:
            return self._resolved_claude_executable

        for candidate in self._iter_candidate_executables():
            try:
                if candidate.exists():
                    self._resolved_claude_executable = str(candidate)
                    return self._resolved_claude_executable
            except OSError:
                continue

        return None

    def build_command(self) -> list[str]:
        resolved = self.resolve_claude_executable()

        if os.name == "nt":
            if resolved:
                suffix = Path(resolved).suffix.lower()
                if suffix in {".cmd", ".bat"}:
                    return ["cmd.exe", "/d", "/c", resolved]
                return [resolved]
            return ["cmd.exe", "/d", "/c", self.executable]

        return [resolved or self.executable]

    def _augment_env_with_claude_path(self, env: dict[str, str]) -> None:
        resolved = self.resolve_claude_executable()
        if not resolved:
            return

        executable_dir = str(Path(resolved).resolve().parent)
        current_path = env.get("PATH", "")
        path_parts = current_path.split(os.pathsep) if current_path else []
        if executable_dir not in path_parts:
            env["PATH"] = executable_dir + (os.pathsep + current_path if current_path else "")

    def build_install_command(self) -> list[str]:
        """构建安装命令，使用淘宝 npm 镜像，不弹出黑色命令行窗口。"""
        install_args = f"npm install -g {self.install_package} --registry={_NPM_REGISTRY}"

        if os.name != "nt":
            return ["npm", "install", "-g", self.install_package,
                    f"--registry={_NPM_REGISTRY}"]

        powershell = shutil.which("powershell") or shutil.which("powershell.exe")
        if powershell:
            return [
                powershell,
                "-NoLogo",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                install_args,
            ]

        comspec = os.environ.get("COMSPEC") or shutil.which("cmd") or "cmd.exe"
        return [comspec, "/d", "/c", install_args]

    def install_claude_code(
        self,
        proxy: ProxyConfig | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """
        使用淘宝源安装 Claude Code，隐藏命令行窗口（Windows）。
        """
        command = self.build_install_command()

        # Windows 下使用 CREATE_NO_WINDOW 标志，避免弹出黑色命令行窗口
        kwargs: dict = {
            "check": False,
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "env": self.build_proxy_process_env(proxy or ProxyConfig()),
        }
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

        result = subprocess.run(command, **kwargs)
        self._resolved_claude_executable = None
        return result

    def build_upgrade_command(self) -> list[str]:
        """构建升级命令，使用淘宝 npm 镜像。"""
        upgrade_args = (
            f"npm update -g {self.install_package} --registry={_NPM_REGISTRY}"
        )

        if os.name != "nt":
            return [
                "npm", "update", "-g", self.install_package,
                f"--registry={_NPM_REGISTRY}",
            ]

        powershell = shutil.which("powershell") or shutil.which("powershell.exe")
        if powershell:
            return [
                powershell,
                "-NoLogo",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                upgrade_args,
            ]

        comspec = os.environ.get("COMSPEC") or shutil.which("cmd") or "cmd.exe"
        return [comspec, "/d", "/c", upgrade_args]

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
        kwargs: dict = {
            "check": False,
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "env": self.build_proxy_process_env(proxy or ProxyConfig()),
        }
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        try:
            result = subprocess.run(command, **kwargs)
            if result.returncode != 0:
                return None
            data = json.loads(result.stdout)
            if installed:
                package = (data.get("dependencies") or {}).get(self.install_package) or {}
                version = package.get("version")
            else:
                version = data
            return str(version).strip() if version else None
        except (OSError, ValueError, TypeError):
            return None

    def upgrade_claude_code(self) -> subprocess.CompletedProcess[str]:
        """
        使用淘宝源升级 Claude Code 到最新版本，隐藏命令行窗口（Windows）。
        """
        command = self.build_upgrade_command()

        kwargs: dict = {
            "check": False,
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
        }
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

        result = subprocess.run(command, **kwargs)
        self._resolved_claude_executable = None
        return result

    def build_startup_context(self, config: AppConfig) -> tuple[Path, dict[str, str], list[str]]:
        project_path = validate_project_path(config.project_path)
        env = build_env(config)
        self._augment_env_with_claude_path(env)
        command = self.build_command()
        return project_path, env, command

    @staticmethod
    def build_proxy_process_env(proxy: ProxyConfig) -> dict[str, str]:
        env = os.environ.copy()
        apply_proxy_env(env, proxy)
        return env

    @staticmethod
    def is_any_native_running() -> bool:
        for process in psutil.process_iter(["name"]):
            try:
                if str(process.info.get("name") or "").casefold() == "claude.exe":
                    return True
            except psutil.Error:
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
                marker = "\\.vscode\\extensions\\anthropic.claude-code-"
                if marker in process_text and "\\claude.exe" in process_text:
                    return True
            except (OSError, psutil.Error):
                continue
        return False

    @staticmethod
    def _run_hidden(command: list[str]) -> subprocess.CompletedProcess[str]:
        kwargs: dict[str, object] = {
            "check": False,
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
        }
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        return subprocess.run(command, **kwargs)
