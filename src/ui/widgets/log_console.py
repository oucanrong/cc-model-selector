# 路径: src/ui/widgets/log_console.py
# 作用: 日志输出控件

from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMenu, QPlainTextEdit

_DEFAULT_LOG_TEXT = "访问 https://github.com/oucanrong/claude-code-launcher 获取最新版本以及加入技术交流群。"


class LogConsole(QPlainTextEdit):
    def __init__(self) -> None:
        super().__init__()
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_menu)
        self.document().setMaximumBlockCount(5000)
        self._auto_scroll = True
        self.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)
        self.appendPlainText(_DEFAULT_LOG_TEXT)

    def append_entry(self, level: str, text: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.appendPlainText(f"[{timestamp}] [{level}] {text}")
        if self._auto_scroll:
            bar = self.verticalScrollBar()
            bar.setValue(bar.maximum())

    def append_process_output(self, text: str) -> None:
        self.append_entry("OUT", text)

    def clear_logs(self) -> None:
        self.clear()
        self.appendPlainText(_DEFAULT_LOG_TEXT)

    def _on_scroll_changed(self, value: int) -> None:
        bar = self.verticalScrollBar()
        self._auto_scroll = value >= bar.maximum() - 2

    def _open_menu(self, pos) -> None:
        menu = QMenu(self)
        copy_action = menu.addAction("复制")
        select_all_action = menu.addAction("全选")
        clear_action = menu.addAction("清空")
        chosen = menu.exec(self.mapToGlobal(pos))
        if chosen == copy_action:
            self.copy()
        elif chosen == select_all_action:
            self.selectAll()
        elif chosen == clear_action:
            self.clear_logs()
