# 路径: C:\Users\oucan\Documents\vscode\claude_code启动器\src\ui\styles.py
# 作用: 全局样式定义（深色按钮配色，白字更清晰易读）

APP_QSS = r'''
QWidget {
    background-color: #ffffff;
    color: #222222;
    font-family: "Microsoft YaHei";
    font-size: 12pt;
}
QMainWindow {
    background-color: #ffffff;
    color: #222222;
}
QGroupBox {
    border: 1px solid #d9d9d9;
    border-radius: 8px;
    margin-top: 12px;
    padding: 10px;
    color: #222222;
    font-weight: 600;
    background-color: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QLineEdit, QComboBox, QPlainTextEdit {
    background-color: #ffffff;
    color: #222222;
    border: 1px solid #cfcfcf;
    border-radius: 6px;
    padding: 3px 6px;
    min-height: 26px;
    selection-background-color: #007acc;
    selection-color: #ffffff;
}
QLineEdit:disabled, QComboBox:disabled {
    color: #888888;
    background-color: #f3f3f3;
}
QPushButton {
    border: none;
    border-radius: 8px;
    padding: 5px 14px;
    min-height: 26px;
    color: white;
}
QPushButton:pressed {
    padding-top: 7px;
    padding-bottom: 3px;
}
QPushButton:disabled {
    background-color: #5a5a5a;
    color: #aaaaaa;
}
QLabel {
    color: #222222;
    background-color: transparent;
}
QStatusBar {
    background-color: #ffffff;
    color: #222222;
    border-top: 1px solid #d9d9d9;
}

/* ── 启动按钮 · 深绿色（与鉴权弹窗"申请API"一致） ── */
QPushButton#startButton {
    background-color: #2ea043;
}
QPushButton#startButton:hover {
    background-color: #238636;
}
QPushButton#startButton:pressed {
    background-color: #196c2e;
}

/* ── 停止按钮 · 深红色 ── */
QPushButton#stopButton {
    background-color: #cf222e;
}
QPushButton#stopButton:hover {
    background-color: #a40e26;
}
QPushButton#stopButton:pressed {
    background-color: #7d0a1a;
}

/* ── 复制日志按钮 · 深紫色 ── */
QPushButton#copyButton {
    background-color: #8250df;
}
QPushButton#copyButton:hover {
    background-color: #6a3cc7;
}
QPushButton#copyButton:pressed {
    background-color: #512da0;
}

/* ── 清空日志按钮 · 深琥珀色 ── */
QPushButton#clearButton {
    background-color: #d29922;
}
QPushButton#clearButton:hover {
    background-color: #b0881b;
}
QPushButton#clearButton:pressed {
    background-color: #8a6a15;
}

/* ── 重置按钮 · 深蓝色 ── */
QPushButton#resetButton {
    background-color: #1f6feb;
}
QPushButton#resetButton:hover {
    background-color: #1158c7;
}
QPushButton#resetButton:pressed {
    background-color: #0d4199;
}

/* ── 升级Claude Code 按钮 · 深青绿色 ── */
QPushButton#upgradeCCButton {
    background-color: #0d9488;
}
QPushButton#upgradeCCButton:hover {
    background-color: #0b7a70;
}
QPushButton#upgradeCCButton:pressed {
    background-color: #096058;
}

/* ── 退出按钮 · 深灰色 ── */
QPushButton#exitButton {
    background-color: #6e7681;
}
QPushButton#exitButton:hover {
    background-color: #545d68;
}
QPushButton#exitButton:pressed {
    background-color: #3d444d;
}

/* ── 鉴权设置按钮 · 深绿色 ── */
QPushButton#authSettingsButton {
    background-color: #2ea043;
}
QPushButton#authSettingsButton:hover {
    background-color: #238636;
}
QPushButton#authSettingsButton:pressed {
    background-color: #196c2e;
}

/* ── 选择工作目录按钮 · 深绿色 ── */
QPushButton#pickProjectButton {
    background-color: #2ea043;
}
QPushButton#pickProjectButton:hover {
    background-color: #238636;
}
QPushButton#pickProjectButton:pressed {
    background-color: #196c2e;
}
'''