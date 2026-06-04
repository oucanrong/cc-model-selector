# 路径: C:\Users\oucan\Documents\vscode\claude_code启动器\src\workers\claude_worker.py
# 作用: Claude Code 启动异步线程（启动与升级分离，升级可中断）

from __future__ import annotations

import os
import subprocess
import threading
import time
import webbrowser

from PyQt6.QtCore import QThread, pyqtSignal

from src.core.config_manager import AppConfig
from src.core.logger import setup_logger
from src.core.process_manager import ProcessManager
from src.services.claude_service import ClaudeService


class ClaudeWorker(QThread):
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int)
    error_signal = pyqtSignal(str)
    # npm 未安装时通知主线程弹窗（携带下载页 URL）
    npm_not_found_signal = pyqtSignal(str)
    # Claude Code 安装成功后通知主线程弹窗并退出
    install_success_signal = pyqtSignal()
    # 安装进度（0-100）
    install_progress_signal = pyqtSignal(int, str)

    def __init__(
        self,
        config: AppConfig,
        process_manager: ProcessManager,
        upgrade_only: bool = False,
    ) -> None:
        super().__init__()
        self.config = config
        self.process_manager = process_manager
        self.service = ClaudeService()
        self.logger = setup_logger()
        self._stop_requested = False
        # 升级专用模式：为 True 时 run() 仅执行升级操作
        self.upgrade_only = upgrade_only
        # 升级子进程句柄（用于中断升级）
        self._upgrade_proc: subprocess.Popen[str] | None = None

    def _emit_process_output(self, prefix: str, text: str) -> None:
        if not text:
            return
        for line in text.splitlines():
            line = line.rstrip()
            if line:
                self.log_signal.emit(f"[{prefix}] {line}")

    # ------------------------------------------------------------------
    # 升级 Claude Code（可被 stop 中断）
    # ------------------------------------------------------------------

    def _try_upgrade_claude(self) -> bool:
        """
        尝试升级 Claude Code 到最新版本。
        使用 subprocess.Popen 以支持用户中途停止。
        返回 True 表示升级成功或被中断；返回 False 表示出错。
        """
        self.status_signal.emit("正在检查 Claude Code 更新 ...")
        self.log_signal.emit("[SYSTEM] 正在检查 Claude Code 更新 ...")

        command = self.service.build_upgrade_command()
        kwargs: dict = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
        }
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

        try:
            self._upgrade_proc = subprocess.Popen(command, **kwargs)

            # 用线程异步读取 stdout / stderr，避免管道阻塞
            def _read_stream(stream, prefix):
                try:
                    for line in iter(stream.readline, ""):
                        if line:
                            self._emit_process_output(prefix, line)
                except (ValueError, OSError):
                    pass
                finally:
                    try:
                        stream.close()
                    except Exception:
                        pass

            t_stdout = threading.Thread(
                target=_read_stream,
                args=(self._upgrade_proc.stdout, "UPGRADE"),
                daemon=True,
            )
            t_stderr = threading.Thread(
                target=_read_stream,
                args=(self._upgrade_proc.stderr, "UPGRADE"),
                daemon=True,
            )
            t_stdout.start()
            t_stderr.start()

            # 轮询等待进程结束，同时响应停止请求
            while self._upgrade_proc.poll() is None:
                if self._stop_requested:
                    self._upgrade_proc.terminate()
                    self.status_signal.emit("升级已被用户中止。")
                    self.log_signal.emit("[SYSTEM] 升级已被用户中止。")
                    return True
                time.sleep(0.1)

            t_stdout.join(timeout=2)
            t_stderr.join(timeout=2)

            returncode = self._upgrade_proc.returncode
            if returncode == 0:
                self.status_signal.emit("Claude Code 升级完成。")
                self.log_signal.emit("[SYSTEM] Claude Code 升级完成。")
            else:
                self.log_signal.emit(
                    f"[SYSTEM] Claude Code 升级结束（返回码: {returncode}）。"
                )
            return True
        except Exception as exc:
            self.logger.exception("升级 Claude Code 失败")
            self.log_signal.emit(f"[SYSTEM] Claude Code 升级失败: {exc}")
            return False
        finally:
            self._upgrade_proc = None

    # ------------------------------------------------------------------
    # 确保 claude 可用（原有逻辑，已移除内嵌升级）
    # ------------------------------------------------------------------

    def _ensure_claude_ready(self) -> bool:
        """
        确保 claude 命令可用。
        返回 True 表示可以继续启动；返回 False 表示本次流程已被中断。
        """
        if self.service.check_claude_installed():
            return True

        self.status_signal.emit("未检测到 claude，开始检查 npm ...")
        self.log_signal.emit("[SYSTEM] 未检测到 claude，开始检查 npm ...")

        if not self.service.check_npm_installed():
            self.status_signal.emit("未检测到 npm，已打开 Node.js 下载页面。")
            self.log_signal.emit("[SYSTEM] 未检测到 npm，已自动打开 Node.js 下载页面。")
            self.npm_not_found_signal.emit(self.service.node_download_url)
            return False

        # npm 存在，开始安装 Claude Code
        self.status_signal.emit("检测到 npm，正在通过淘宝源自动安装 Claude Code ...")
        self.log_signal.emit("[SYSTEM] 检测到 npm，正在通过淘宝源自动安装 Claude Code ...")
        self.install_progress_signal.emit(10, "正在安装 Claude Code，请稍候...")

        result = self.service.install_claude_code()

        self.install_progress_signal.emit(80, "安装命令已执行，正在验证...")

        if result.stdout:
            self._emit_process_output("INSTALL", result.stdout)
        if result.stderr:
            self._emit_process_output("INSTALL-ERR", result.stderr)

        if result.returncode != 0:
            self.install_progress_signal.emit(0, "")
            raise RuntimeError(
                "Claude Code 自动安装失败，请检查 npm / 网络 / 权限后重试。"
            )

        if not self.service.check_claude_installed():
            self.install_progress_signal.emit(0, "")
            raise RuntimeError(
                "Claude Code 安装完成，但当前环境仍未检测到 claude 命令。"
                "请确认 npm 全局路径已加入 PATH，然后重新启动本程序。"
            )

        self.install_progress_signal.emit(100, "安装完成！")
        self.status_signal.emit("Claude Code 安装完成。")
        self.log_signal.emit("[SYSTEM] Claude Code 安装完成。")

        # 通知主线程弹窗提示安装成功，并退出程序
        self.install_success_signal.emit()
        return False

    # ------------------------------------------------------------------
    # run()
    # ------------------------------------------------------------------

    def run(self) -> None:
        if self.upgrade_only:
            self._run_upgrade()
        else:
            self._run_launch()

    def _run_upgrade(self) -> None:
        """仅执行升级操作。"""
        try:
            self._try_upgrade_claude()
            self.finished_signal.emit(0)
        except Exception as exc:
            self.logger.exception("升级 Claude Code 失败")
            self.error_signal.emit(str(exc))

    def _run_launch(self) -> None:
        """执行启动 Claude Code 的完整流程（不含升级）。"""
        try:
            if not self._ensure_claude_ready():
                return

            cwd, env, command = self.service.build_startup_context(self.config)
            self.status_signal.emit(f"正在启动 Claude Code：{cwd}")
            self.log_signal.emit(f"[SYSTEM] 工作目录：{cwd}")
            self.log_signal.emit(f"[SYSTEM] 启动命令：{' '.join(command)}")

            proc = self.process_manager.start(command=command, cwd=cwd, env=env)
            self.status_signal.emit("Claude Code 已在独立终端中启动。")
            self.log_signal.emit("[SYSTEM] Claude Code 已在独立终端中启动。")

            return_code = proc.wait()
            self.status_signal.emit(f"Claude Code 已退出，返回码：{return_code}")
            self.finished_signal.emit(return_code)
        except Exception as exc:
            self.logger.exception("启动 Claude Code 失败")
            self.error_signal.emit(str(exc))

    # ------------------------------------------------------------------
    # 停止
    # ------------------------------------------------------------------

    def request_soft_stop(self) -> None:
        self._stop_requested = True
        # 如果正在升级，终止升级子进程
        if self._upgrade_proc is not None and self._upgrade_proc.poll() is None:
            self._upgrade_proc.terminate()
            return
        # 否则停止 Claude Code 进程
        if not self.process_manager.stop_soft():
            self.process_manager.stop_hard()

    def request_hard_stop(self) -> None:
        self._stop_requested = True
        # 如果正在升级，强制杀死升级子进程
        if self._upgrade_proc is not None:
            try:
                self._upgrade_proc.kill()
            except Exception:
                pass
            return
        # 否则强制停止 Claude Code 进程
        self.process_manager.stop_hard()
