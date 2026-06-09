# 更新日志

## Codex 供应商推理能力修订

- DeepSeek 推理强度调整为“关闭、high、max”，并修正兼容映射。
- Kimi、智谱 GLM、小米 MiMo 新增独立思考模式开关，默认开启。
- 千问、MiniMax 和 GPT 中转继续使用原有 Responses API 直连配置。
- 方舟 Coding Plan 暂不提供统一思考开关。
- 本次仅修改 Codex，Claude Code 未改动。

## 协议说明

- DeepSeek 使用 Chat Completions，并接收 `thinking` 与
  `reasoning_effort`。
- Kimi、智谱 GLM、小米 MiMo 使用 Chat Completions，并接收
  `thinking.type=enabled/disabled`，不提供推理强度档位。
- 千问、MiniMax 和 GPT 中转由 Codex 直接调用 Responses API，
  不经过本地转换代理。
