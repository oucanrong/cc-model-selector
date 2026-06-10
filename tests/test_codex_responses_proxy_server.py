from __future__ import annotations

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx

from src.core.config_manager import ProxyConfig
from src.services.codex_responses_protocol import prepare_ark_request
from src.services.codex_responses_proxy_server import (
    CodexResponsesProxyServer,
)


class CodexResponsesProxyServerTests(unittest.TestCase):
    def test_reasoning_modes_and_unrelated_fields_are_preserved(self) -> None:
        body = {
            "model": "client-model",
            "input": "hello",
            "max_output_tokens": 4096,
            "previous_response_id": "resp_previous",
            "reasoning": {"effort": "low", "summary": "auto"},
            "store": False,
        }
        doubao, _registry = prepare_ark_request(
            body,
            "doubao-seed-2.0-code",
            "effort",
            "medium",
            False,
        )
        self.assertEqual(doubao["model"], "doubao-seed-2.0-code")
        self.assertEqual(doubao["thinking"], {"type": "enabled"})
        self.assertEqual(
            doubao["reasoning"],
            {"effort": "low", "summary": "auto"},
        )
        self.assertEqual(doubao["max_output_tokens"], 4096)
        self.assertEqual(doubao["previous_response_id"], "resp_previous")
        self.assertFalse(doubao["store"])

        minimal, _registry = prepare_ark_request(
            {"input": "hello", "reasoning": {"effort": "minimal"}},
            "doubao-seed-2.0-lite",
            "effort",
            "medium",
            True,
        )
        self.assertEqual(minimal["thinking"], {"type": "disabled"})
        self.assertEqual(minimal["reasoning"], {"effort": "minimal"})

        deepseek, _registry = prepare_ark_request(
            body,
            "deepseek-v4-pro",
            "toggle",
            "",
            False,
        )
        self.assertEqual(deepseek["thinking"], {"type": "disabled"})
        self.assertNotIn("reasoning", deepseek)

        minimax, _registry = prepare_ark_request(
            body,
            "minimax-latest",
            "none",
            "",
            False,
        )
        self.assertNotIn("thinking", minimax)
        self.assertNotIn("reasoning", minimax)

    def test_non_streaming_custom_tool_round_trip(self) -> None:
        captured: dict[str, object] = {}

        class UpstreamHandler(BaseHTTPRequestHandler):
            def log_message(self, _format, *_args):
                return

            def do_POST(self):
                captured["path"] = self.path
                captured["authorization"] = self.headers.get("Authorization")
                length = int(self.headers["Content-Length"])
                captured["body"] = json.loads(self.rfile.read(length))
                response = {
                    "id": "resp_1",
                    "object": "response",
                    "status": "completed",
                    "model": "doubao-seed-2.0-code",
                    "output": [
                        {
                            "id": "fc_1",
                            "type": "function_call",
                            "status": "completed",
                            "call_id": "call_1",
                            "name": "apply_patch",
                            "arguments": '{"input":"*** Begin Patch"}',
                        }
                    ],
                }
                data = json.dumps(response).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        upstream, thread = self._start_upstream(UpstreamHandler)
        router = CodexResponsesProxyServer(
            upstream_base_url=(
                f"http://127.0.0.1:{upstream.server_address[1]}/api/coding/v3"
            ),
            api_key="ark-key",
            model="doubao-seed-2.0-code",
            proxy=ProxyConfig(),
            reasoning_control="effort",
            reasoning_effort="medium",
            thinking_enabled=True,
        )
        router.start()
        try:
            with httpx.Client(trust_env=False) as client:
                response = client.post(
                    f"{router.base_url}/responses",
                    json={
                        "input": "edit",
                        "reasoning": {"effort": "high"},
                        "max_output_tokens": 2048,
                        "tools": [
                            {
                                "type": "custom",
                                "name": "apply_patch",
                                "description": "Apply a patch",
                            }
                        ],
                        "tool_choice": {
                            "type": "custom",
                            "name": "apply_patch",
                        },
                    },
                    timeout=5,
                )
            self.assertEqual(response.status_code, 200, response.text)
            request_body = captured["body"]
            self.assertIsInstance(request_body, dict)
            self.assertEqual(captured["path"], "/api/coding/v3/responses")
            self.assertEqual(captured["authorization"], "Bearer ark-key")
            self.assertEqual(request_body["thinking"], {"type": "enabled"})
            self.assertEqual(request_body["reasoning"], {"effort": "high"})
            self.assertEqual(request_body["max_output_tokens"], 2048)
            self.assertEqual(request_body["tools"][0]["type"], "function")
            self.assertEqual(
                request_body["tools"][0]["parameters"]["required"],
                ["input"],
            )
            self.assertEqual(
                request_body["tool_choice"],
                {"type": "function", "name": "apply_patch"},
            )
            item = response.json()["output"][0]
            self.assertEqual(item["type"], "custom_tool_call")
            self.assertEqual(item["name"], "apply_patch")
            self.assertEqual(item["input"], "*** Begin Patch")
        finally:
            router.stop()
            self._stop_upstream(upstream, thread)

    def test_streaming_custom_tool_events_are_restored(self) -> None:
        class UpstreamHandler(BaseHTTPRequestHandler):
            def log_message(self, _format, *_args):
                return

            def do_POST(self):
                length = int(self.headers["Content-Length"])
                self.rfile.read(length)
                events = [
                    {
                        "type": "response.output_item.added",
                        "output_index": 0,
                        "item": {
                            "id": "fc_1",
                            "type": "function_call",
                            "status": "in_progress",
                            "call_id": "call_1",
                            "name": "apply_patch",
                            "arguments": "",
                        },
                    },
                    {
                        "type": "response.function_call_arguments.delta",
                        "item_id": "fc_1",
                        "output_index": 0,
                        "delta": '{"input":"patch"}',
                    },
                    {
                        "type": "response.function_call_arguments.done",
                        "item_id": "fc_1",
                        "output_index": 0,
                        "arguments": '{"input":"patch"}',
                    },
                    {
                        "type": "response.output_item.done",
                        "output_index": 0,
                        "item": {
                            "id": "fc_1",
                            "type": "function_call",
                            "status": "completed",
                            "call_id": "call_1",
                            "name": "apply_patch",
                            "arguments": '{"input":"patch"}',
                        },
                    },
                    {
                        "type": "response.completed",
                        "response": {
                            "id": "resp_1",
                            "object": "response",
                            "status": "completed",
                            "output": [
                                {
                                    "id": "fc_1",
                                    "type": "function_call",
                                    "status": "completed",
                                    "call_id": "call_1",
                                    "name": "apply_patch",
                                    "arguments": '{"input":"patch"}',
                                }
                            ],
                        },
                    },
                ]
                data = "".join(
                    f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
                    for event in events
                ) + "data: [DONE]\n\n"
                encoded = data.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

        upstream, thread = self._start_upstream(UpstreamHandler)
        router = CodexResponsesProxyServer(
            upstream_base_url=f"http://127.0.0.1:{upstream.server_address[1]}",
            api_key="key",
            model="doubao-seed-2.0-code",
            proxy=ProxyConfig(),
            reasoning_control="effort",
            reasoning_effort="medium",
            thinking_enabled=True,
        )
        router.start()
        try:
            with httpx.Client(trust_env=False) as client:
                response = client.post(
                    f"{router.base_url}/responses",
                    json={
                        "input": "edit",
                        "stream": True,
                        "tools": [{"type": "custom", "name": "apply_patch"}],
                    },
                    timeout=5,
                )
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIn('"type": "custom_tool_call"', response.text)
            self.assertIn(
                "event: response.custom_tool_call_input.done",
                response.text,
            )
            self.assertIn('"input": "patch"', response.text)
            self.assertNotIn(
                "event: response.function_call_arguments.delta",
                response.text,
            )
        finally:
            router.stop()
            self._stop_upstream(upstream, thread)

    @staticmethod
    def _start_upstream(handler):
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread

    @staticmethod
    def _stop_upstream(server, thread) -> None:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
