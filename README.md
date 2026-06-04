# claude-code-model-manager (Claude Code 模型管理器)

一款专门为 Anthropic 官方命令行 AI 助手 `claude-code` 打造的 Windows 图形化启动与配置管理工具。基于 Python 3.14 + PyQt6 构建，旨在消除 Windows 环境下繁琐的环境变量配置、多端大模型鉴权及网络代理障碍。

## ✨ 核心特性

- **🚀 跨服务商快速适配**：预设 Claude 官方、DeepSeek、Kimi、智谱 GLM、阿里千问、MINIMAX、第三方中转API服务的Anthropic 兼容端预设，一键注入对应的 API Key / Token。
- **🌐 全功能网络代理支持**：完美集成 **HTTP、HTTPS、SOCKS5** 三种代理协议，国内网络环境无缝使用。
- **📂 智能工作区与多项目管理**：支持可视化选择工作目录，自动维护历史项目记录，一键切换。
- **🛠 独立控制台拉起**：采用多进程与多线程管理，在独立的安全控制台中拉起 Claude 交互界面，绝不卡死主 GUI。
- **📦 自动化打包集成**：内置 `build_exe.py` 脚本，一键将项目编译成独立的 `.exe` 程序。
- **🌐支持第3方中转API**：支持第三方提供的Claude和GPT的API中转服务。

## 📋 系统要求

- **操作系统**：Windows 11 (推荐) / Windows 10
- **运行环境**：Node.js & npm (用于全局运行 claude-code)
- **开发环境** (仅从源码运行需要)：Python 3.14+

## 🚀 快捷使用说明

### 选项 A：直接运行打包好的可执行文件（推荐普通用户使用）

1. 前往本仓库右侧的 [Releases](https://github.com/oucanrong/cc-model-manager/releases) 页面。
2. 下载最新版本的压缩包并解压。
3. 双击 `Claude-Code模型管理器.exe` 即可启动图形界面。
4. 运行界面

4.1 选择Claude Code默认参数

![选择Claude Code默认参数](https://github.com/oucanrong/cc-model-manager/blob/main/screenshot/01-claude.png)

4.2 调用deepseek模型

![选择deepseek模型](https://github.com/oucanrong/cc-model-manager/blob/main/screenshot/02-deepseek.png)
![运行deepseek模型](https://github.com/oucanrong/cc-model-manager/blob/main/screenshot/02b-deepseek.png)

4.3 调用kimi模型
![选择kimi模型](https://github.com/oucanrong/cc-model-manager/blob/main/screenshot/03-kimi.png)
![运行kimi模型](https://github.com/oucanrong/cc-model-manager/blob/main/screenshot/03b-kimi.png)

4.4 调用智谱模型
![选择智谱模型](https://github.com/oucanrong/cc-model-manager/blob/main/screenshot/04-gml.png)
![运行智谱模型](https://github.com/oucanrong/cc-model-manager/blob/main/screenshot/04b-gml.png)

4.5 支持阿里千问
![选择阿里千问](https://github.com/oucanrong/cc-model-manager/blob/main/screenshot/05-qwen.png)
![使用阿里千问](https://github.com/oucanrong/cc-model-manager/blob/main/screenshot/05b-qwen.png)

4.6 MINIMAX
![选择MINIMAX](https://github.com/oucanrong/cc-model-manager/blob/main/screenshot/06-minimax.png)

4.7 支持第3方claude中转
![选择3方claude中转](https://github.com/oucanrong/cc-model-manager/blob/main/screenshot/07-claude-proxy.png)

![使用3方claude中转](https://github.com/oucanrong/cc-model-manager/blob/main/screenshot/07b-claude-proxy.png)

### 选项 B：从源码运行（适合开发者）

1. **克隆本仓库**：

   ```bash
   git clone https://github.com/oucanrong/cc-model-manager.git
   cd cc-model-manager

2. 安装依赖：

```
pip install PyQt6 psutil Pillow PyInstaller
```

3. 运行主程序：

```
python main.py
```

技术交流群：

![技术交流群](https://github.com/oucanrong/cc-model-manager/blob/main/screenshot/qrcode.png)

如有Mac和Linux版本的需要，也可加群。看需求，有时间再做。