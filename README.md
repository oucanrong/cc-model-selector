# CC模型管理器

`cc模型管理器` 是面向 Windows 的 Claude Code 与 Codex 图形化启动、鉴权和模型配置工具。它可以在一个界面中管理 API 供应商、模型、代理和工作目录，并启动桌面端、CLI 或 VS Code。

## 主要功能

- 🤖 同时管理 Claude Code 和 Codex，两套鉴权与配置互相独立。
- 🌐 支持 Claude/Codex 官方接口、DeepSeek、Kimi、智谱GLM、阿里千问、MiniMax、小米MiMo、方舟Coding Plan，以及 Claude/GPT 中转服务。
- 🚀 支持 Claude Code 桌面版、Claude Code CLI、Codex 桌面端、Codex CLI 和 VS Code。
- 🔄 支持检查并升级 Claude Code CLI 与 Codex CLI；已是最新版本时直接提示，无须重复升级。
- 📦 系统已安装 npm 但缺少 CLI 时，可自动安装对应 CLI。
- 🔌 支持 HTTP、HTTPS、SOCKS5 代理，并传递给启动的子进程。
- 🔁 Codex 可直连兼容 Responses API 的供应商，也可通过本地随机端口在 Responses API 与 Chat Completions API 之间转换。
- 🛡️ 启动前临时修改 Claude/Codex 配置，正常退出、停止或异常恢复时还原原始文件。
- 🔑 API Key 明文保存在本软件的本地 `config.json` 中，请妥善保管。

## 界面预览

### Claude Code API 供应商

![Claude Code API 供应商](https://github.com/oucanrong/cc-model-manager/blob/main/screenshot/01-claude-code-providers.png)

### Claude Code 启动目标

![Claude Code 启动目标](https://github.com/oucanrong/cc-model-manager/blob/main/screenshot/02-claude-code-launcher.png)

### Codex API 供应商

![Codex API 供应商](https://github.com/oucanrong/cc-model-manager/blob/main/screenshot/03-codex-providers.png)

### Codex 启动目标

![Codex 启动目标](https://github.com/oucanrong/cc-model-manager/blob/main/screenshot/04-codex-launcher.png)

## 系统要求

- Windows 11，或兼容的 Windows 10 环境。
- 使用 CLI 或升级功能时需要 Node.js 与 npm。
- 从源码运行需要 Python 3.14 和项目依赖。
- 桌面端、VS Code 启动目标需要用户安装对应应用。

## 使用发行版

1. 前往 [GitHub Releases](https://github.com/oucanrong/cc-model-manager/releases)。
2. 下载并解压最新版本。
3. 运行 `cc模型管理器.exe`。
4. 在“鉴权设置”中填写第三方供应商的 Base URL 和 API Key。
5. 选择 API 供应商、模型、启动目标和工作目录，然后点击“启动”。

官方接口继续使用用户已有的官方登录状态。第三方接口会根据启动目标通过子进程环境变量或临时配置传递鉴权信息。

## 从源码运行

```powershell
git clone https://github.com/oucanrong/cc-model-manager.git
cd cc-model-manager
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## 测试与打包

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe build_exe.py
```

打包结果位于 `dist\cc模型管理器\`。

## 技术交流群

![技术交流群](https://github.com/oucanrong/cc-model-manager/blob/main/screenshot/qrcode.png)

项目目前主要支持 Windows。其他系统版本将根据实际需求评估。
