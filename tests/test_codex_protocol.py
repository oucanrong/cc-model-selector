from __future__ import annotations

import json
import threading
import unittest

from src.services.codex_protocol import (
    ChatStreamToResponses,
    ResponseHistoryCache,
    chat_to_response,
    normalize_error,
    responses_to_chat,
)


class CodexProtocolTests(unittest.TestCase):
    def test_responses_request_maps_messages_reasoning_and_custom_tool(self) -> None:
        body = {
            "model": "ignored",
            "instructions": "Be precise.",
            "reasoning": {"effort": "xhigh"},
            "tools": [
                {
                    "type": "custom",
                    "name": "apply_patch",
                    "description": "Apply a patch.",
                }
            ],
            "tool_choice": {"type": "custom", "name": "apply_patch"},
            "input": [
                {"type": "message", "role": "user", "content": "Fix it"},
                {
                    "type": "custom_tool_call",
                    "call_id": "call_1",
                    "name": "apply_patch",
                    "input": "*** Begin Patch\n*** End Patch",
                },
            ],
        }
        result = responses_to_chat(body, "deepseek-v4-pro")
        self.assertEqual(result["model"], "deepseek-v4-pro")
        self.assertEqual(result["messages"][0]["role"], "system")
        self.assertEqual(
            result["tools"][0]["function"]["parameters"]["required"],
            ["input"],
        )
        arguments = result["messages"][-1]["tool_calls"][0]["function"]["arguments"]
        self.assertEqual(json.loads(arguments)["input"], "*** Begin Patch\n*** End Patch")
        self.assertEqual(result["reasoning_effort"], "max")

    def test_chat_response_restores_custom_tool(self) -> None:
        chat = {
            "id": "chat_1",
            "model": "kimi-k2.6",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "apply_patch",
                                    "arguments": '{"input":"patch text"}',
                                },
                            }
                        ],
                    }
                }
            ],
        }
        result = chat_to_response(chat, "kimi-k2.6", {"apply_patch"})
        self.assertEqual(result["output"][0]["type"], "custom_tool_call")
        self.assertEqual(result["output"][0]["input"], "patch text")

    def test_kimi_uses_thinking_without_deepseek_effort_field(self) -> None:
        result = responses_to_chat(
            {
                "input": "hello",
                "reasoning": {"effort": "high"},
            },
            "kimi-k2.6",
        )
        self.assertEqual(result["thinking"], {"type": "enabled"})
        self.assertNotIn("reasoning_effort", result)

    def test_toggle_provider_forces_thinking_without_reasoning_input(self) -> None:
        enabled = responses_to_chat(
            {"input": "hello"},
            "kimi-k2.6",
            capabilities={
                "thinking_param": "thinking",
                "thinking_enabled": True,
            },
        )
        disabled = responses_to_chat(
            {
                "input": "hello",
                "reasoning": {"effort": "high"},
            },
            "mimo-v2.5-pro",
            capabilities={
                "thinking_param": "thinking",
                "effort_param": "reasoning_effort",
                "thinking_enabled": False,
            },
        )
        self.assertEqual(enabled["thinking"], {"type": "enabled"})
        self.assertEqual(disabled["thinking"], {"type": "disabled"})
        self.assertNotIn("reasoning_effort", disabled)

    def test_deepseek_effort_compatibility_mapping(self) -> None:
        capabilities = {
            "thinking_param": "thinking",
            "effort_param": "reasoning_effort",
            "effort_map": {
                "low": "high",
                "medium": "high",
                "xhigh": "max",
            },
        }
        for source, expected in (
            ("low", "high"),
            ("medium", "high"),
            ("high", "high"),
            ("xhigh", "max"),
            ("max", "max"),
        ):
            result = responses_to_chat(
                {
                    "input": "hello",
                    "reasoning": {"effort": source},
                },
                "deepseek-v4-pro",
                capabilities=capabilities,
            )
            self.assertEqual(result["thinking"], {"type": "enabled"})
            self.assertEqual(result["reasoning_effort"], expected)

        disabled = responses_to_chat(
            {
                "input": "hello",
                "reasoning": {"effort": "none"},
            },
            "deepseek-v4-pro",
            capabilities=capabilities,
        )
        self.assertEqual(disabled["thinking"], {"type": "disabled"})
        self.assertNotIn("reasoning_effort", disabled)

    def test_stream_emits_text_reasoning_usage_and_custom_tool_events(self) -> None:
        converter = ChatStreamToResponses("glm-5.1", {"apply_patch"})
        output = b"".join(
            [
                *converter.start_events(),
                *converter.feed(
                    {
                        "choices": [
                            {"delta": {"reasoning_content": "thinking"}}
                        ]
                    }
                ),
                *converter.feed(
                    {"choices": [{"delta": {"content": "answer"}}]}
                ),
                *converter.feed(
                    {
                        "choices": [
                            {
                                "delta": {
                                    "tool_calls": [
                                        {
                                            "index": 0,
                                            "id": "call_1",
                                            "function": {
                                                "name": "apply_patch",
                                                "arguments": '{"input":"patch"}',
                                            },
                                        }
                                    ]
                                }
                            }
                        ],
                        "usage": {
                            "prompt_tokens": 2,
                            "completion_tokens": 3,
                            "total_tokens": 5,
                        },
                    }
                ),
                *converter.finish_events(),
            ]
        ).decode("utf-8")
        self.assertIn("response.reasoning_summary_text.delta", output)
        self.assertIn("response.output_text.delta", output)
        self.assertIn("response.custom_tool_call_input.done", output)
        self.assertIn('"total_tokens": 5', output)

    def test_request_maps_images_roles_tools_parameters_and_reasoning_close(self) -> None:
        registry = {}
        result = responses_to_chat(
            {
                "instructions": "system",
                "input": [
                    {
                        "type": "message",
                        "role": "developer",
                        "content": "developer",
                    },
                    {
                        "type": "message",
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": "look"},
                            {
                                "type": "input_image",
                                "image_url": "data:image/png;base64,AA==",
                            },
                        ],
                    },
                ],
                "tools": [
                    {
                        "type": "function",
                        "name": "plain",
                        "parameters": '{"type":"object"}',
                    },
                    {"type": "custom", "name": "patch"},
                    {"type": "tool_search"},
                    {
                        "type": "namespace",
                        "name": "github",
                        "tools": [
                            {
                                "type": "function",
                                "name": "search",
                                "parameters": {"type": "object"},
                            }
                        ],
                    },
                ],
                "reasoning": {"effort": "none"},
                "max_output_tokens": 100,
                "parallel_tool_calls": False,
                "seed": 7,
            },
            "deepseek-v4-pro",
            capabilities={
                "thinking_param": "thinking",
                "effort_param": "reasoning_effort",
                "effort_map": {"xhigh": "high"},
            },
            tool_registry=registry,
        )
        self.assertEqual(result["messages"][0]["content"], "system\n\ndeveloper")
        self.assertEqual(result["messages"][1]["content"][1]["type"], "image_url")
        self.assertEqual(
            [tool["function"]["name"] for tool in result["tools"]],
            ["plain", "patch", "tool_search", "github__search"],
        )
        self.assertEqual(registry["github__search"]["namespace"], "github")
        self.assertEqual(result["thinking"], {"type": "disabled"})
        self.assertNotIn("reasoning_effort", result)
        self.assertEqual(result["max_tokens"], 100)
        self.assertFalse(result["parallel_tool_calls"])
        self.assertEqual(result["seed"], 7)

    def test_tool_call_reasoning_uses_real_value_before_placeholder(self) -> None:
        result = responses_to_chat(
            {
                "input": [
                    {
                        "type": "function_call",
                        "call_id": "call_1",
                        "name": "run",
                        "arguments": {"value": 1},
                        "reasoning_content": "real reasoning",
                    }
                ]
            },
            "deepseek-v4-pro",
            capabilities={"tool_call_reasoning_required": True},
        )
        assistant = result["messages"][0]
        self.assertEqual(assistant["reasoning_content"], "real reasoning")
        self.assertEqual(
            assistant["tool_calls"][0]["function"]["arguments"],
            '{"value":1}',
        )

    def test_non_stream_restores_reasoning_refusal_namespace_length_and_usage(self) -> None:
        response = chat_to_response(
            {
                "id": "resp_test",
                "choices": [
                    {
                        "finish_reason": "length",
                        "message": {
                            "content": "<think>inline</think>answer",
                            "refusal": "cannot comply",
                            "reasoning_details": [
                                {"type": "reasoning_text", "text": "details"}
                            ],
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "function": {
                                        "name": "github__search",
                                        "arguments": {"query": "bug"},
                                    },
                                }
                            ],
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 4,
                    "completion_tokens": 5,
                    "total_tokens": 9,
                    "prompt_tokens_details": {"cached_tokens": 2},
                    "completion_tokens_details": {"reasoning_tokens": 3},
                },
            },
            "glm-5.1",
            tool_registry={
                "github__search": {
                    "type": "function",
                    "name": "search",
                    "namespace": "github",
                }
            },
        )
        self.assertEqual(response["status"], "incomplete")
        self.assertEqual(
            response["incomplete_details"]["reason"],
            "max_output_tokens",
        )
        self.assertEqual(response["output"][0]["summary"][0]["text"], "details")
        self.assertEqual(response["output"][1]["content"][0]["text"], "answer")
        self.assertEqual(response["output"][1]["content"][1]["type"], "refusal")
        self.assertEqual(response["output"][2]["name"], "search")
        self.assertEqual(response["output"][2]["namespace"], "github")
        self.assertEqual(
            response["usage"]["input_tokens_details"]["cached_tokens"],
            2,
        )
        self.assertEqual(
            response["usage"]["output_tokens_details"]["reasoning_tokens"],
            3,
        )

    def test_inline_think_is_used_when_structured_reasoning_is_missing(self) -> None:
        response = chat_to_response(
            {
                "choices": [
                    {
                        "message": {
                            "content": "<think>hidden</think>visible",
                        }
                    }
                ]
            },
            "mimo-v2.5",
        )
        self.assertEqual(response["output"][0]["summary"][0]["text"], "hidden")
        self.assertEqual(response["output"][1]["content"][0]["text"], "visible")

    def test_stream_handles_split_think_tags_tool_deltas_and_length(self) -> None:
        converter = ChatStreamToResponses(
            "mimo-v2.5",
            tool_registry={
                "patch": {"type": "custom", "name": "patch", "namespace": ""}
            },
        )
        output = b"".join(
            [
                *converter.start_events(),
                *converter.feed({"choices": [{"delta": {"content": "<thi"}}]}),
                *converter.feed({"choices": [{"delta": {"content": "nk>why"}}]}),
                *converter.feed(
                    {"choices": [{"delta": {"content": "</think>answer"}}]}
                ),
                *converter.feed(
                    {
                        "choices": [
                            {
                                "delta": {
                                    "tool_calls": [
                                        {
                                            "index": 0,
                                            "id": "call_1",
                                            "function": {
                                                "name": "patch",
                                                "arguments": '{"input":"',
                                            },
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ),
                *converter.feed(
                    {
                        "choices": [
                            {
                                "finish_reason": "length",
                                "delta": {
                                    "tool_calls": [
                                        {
                                            "index": 0,
                                            "function": {"arguments": 'x"}'},
                                        }
                                    ]
                                },
                            }
                        ],
                        "usage": {
                            "prompt_tokens": 1,
                            "completion_tokens": 2,
                            "total_tokens": 3,
                        },
                    }
                ),
                *converter.finish_events(),
            ]
        ).decode("utf-8")
        self.assertIn("response.in_progress", output)
        self.assertIn('"delta": "why"', output)
        self.assertIn('"delta": "answer"', output)
        self.assertIn("response.custom_tool_call_input.delta", output)
        self.assertIn("response.incomplete", output)
        self.assertIn('"reason": "max_output_tokens"', output)

    def test_history_restores_by_response_and_unique_call_and_is_thread_safe(self) -> None:
        cache = ResponseHistoryCache(max_entries=2)
        output = [
            {
                "type": "function_call",
                "call_id": "call_1",
                "name": "run",
                "arguments": '{"x":1}',
            }
        ]
        cache.store("resp_1", output)
        self.assertEqual(cache.restore("resp_1", [])[0]["id"], "call_1")
        self.assertEqual(cache.restore(None, ["call_1"])[0]["id"], "call_1")

        threads = [
            threading.Thread(
                target=cache.store,
                args=(
                    f"resp_{index}",
                    [
                        {
                            "type": "function_call",
                            "call_id": f"call_{index}",
                            "name": "run",
                            "arguments": "{}",
                        }
                    ],
                ),
            )
            for index in range(2, 20)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertLessEqual(len(cache), 2)

    def test_history_rejects_ambiguous_call_id(self) -> None:
        cache = ResponseHistoryCache()
        item = [
            {
                "type": "function_call",
                "call_id": "same",
                "name": "run",
                "arguments": "{}",
            }
        ]
        cache.store("resp_1", item)
        cache.store("resp_2", item)
        with self.assertRaisesRegex(ValueError, "多个历史响应"):
            cache.restore(None, ["same"])

    def test_error_normalization_supports_detail_minimax_and_text(self) -> None:
        self.assertEqual(
            normalize_error({"detail": "bad"}, 400)["error"]["message"],
            "bad",
        )
        self.assertEqual(
            normalize_error(
                {"base_resp": {"status_code": 1001, "status_msg": "denied"}},
                401,
            )["error"]["message"],
            "denied",
        )
        self.assertEqual(
            normalize_error(b"plain failure", 502)["error"]["message"],
            "plain failure",
        )

    def test_stream_error_emits_failed_without_completion(self) -> None:
        converter = ChatStreamToResponses("glm-5.1")
        output = b"".join(
            converter.feed({"error": {"message": "stream failed"}})
        ).decode("utf-8")
        self.assertTrue(converter.failed)
        self.assertIn("response.failed", output)
        self.assertNotIn("response.completed", output)


if __name__ == "__main__":
    unittest.main()
