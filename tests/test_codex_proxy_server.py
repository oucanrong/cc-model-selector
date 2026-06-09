from __future__ import annotations

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx

from src.core.config_manager import ProxyConfig
from src.services.codex_proxy_server import CodexProxyServer


class CodexProxyServerTests(unittest.TestCase):
    def test_random_port_proxy_converts_request_and_response(self) -> None:
        captured = {}

        class UpstreamHandler(BaseHTTPRequestHandler):
            def log_message(self, _format, *_args):
                return

            def do_POST(self):
                length = int(self.headers["Content-Length"])
                captured["body"] = json.loads(self.rfile.read(length))
                response = {
                    "id": "chat_1",
                    "model": "deepseek-v4-pro",
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "pong",
                            }
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 1,
                        "completion_tokens": 1,
                        "total_tokens": 2,
                    },
                }
                data = json.dumps(response).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        upstream = ThreadingHTTPServer(("127.0.0.1", 0), UpstreamHandler)
        thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        thread.start()
        logs = []
        router = CodexProxyServer(
            upstream_base_url=f"http://127.0.0.1:{upstream.server_address[1]}",
            api_key="test-key",
            model="deepseek-v4-pro",
            proxy=ProxyConfig(),
            log=logs.append,
        )
        router.start()
        try:
            self.assertGreater(router.port, 0)
            with httpx.Client(trust_env=False) as client:
                response = client.post(
                    f"{router.base_url}/responses",
                    json={
                        "model": "client-model",
                        "input": "ping",
                        "stream": False,
                    },
                    timeout=5,
                )
            self.assertEqual(
                response.status_code,
                200,
                f"{response.text}\nlogs={logs}",
            )
            self.assertEqual(
                captured["body"]["model"],
                "deepseek-v4-pro",
            )
            self.assertEqual(
                response.json()["output"][0]["content"][0]["text"],
                "pong",
            )
        finally:
            router.stop()
            upstream.shutdown()
            upstream.server_close()
            thread.join(timeout=2)

    def test_all_responses_paths_are_accepted(self) -> None:
        class UpstreamHandler(BaseHTTPRequestHandler):
            def log_message(self, _format, *_args):
                return

            def do_POST(self):
                length = int(self.headers["Content-Length"])
                self.rfile.read(length)
                data = json.dumps(
                    {
                        "choices": [
                            {"message": {"role": "assistant", "content": "ok"}}
                        ]
                    }
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        upstream = ThreadingHTTPServer(("127.0.0.1", 0), UpstreamHandler)
        thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        thread.start()
        router = CodexProxyServer(
            upstream_base_url=f"http://127.0.0.1:{upstream.server_address[1]}",
            api_key="key",
            model="kimi-k2.6",
            proxy=ProxyConfig(),
        )
        router.start()
        try:
            with httpx.Client(trust_env=False) as client:
                for path in (
                    "/responses",
                    "/v1/responses",
                    "/responses/compact",
                    "/v1/responses/compact",
                ):
                    response = client.post(
                        f"http://127.0.0.1:{router.port}{path}",
                        json={"input": "ping"},
                        timeout=5,
                    )
                    self.assertEqual(response.status_code, 200, response.text)
        finally:
            router.stop()
            upstream.shutdown()
            upstream.server_close()
            thread.join(timeout=2)

    def test_previous_response_id_restores_tool_call(self) -> None:
        captured = []

        class UpstreamHandler(BaseHTTPRequestHandler):
            def log_message(self, _format, *_args):
                return

            def do_POST(self):
                length = int(self.headers["Content-Length"])
                captured.append(json.loads(self.rfile.read(length)))
                if len(captured) == 1:
                    message = {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "function": {
                                    "name": "run",
                                    "arguments": '{"value":1}',
                                },
                            }
                        ],
                    }
                else:
                    message = {"role": "assistant", "content": "done"}
                data = json.dumps(
                    {
                        "id": f"resp_{len(captured)}",
                        "choices": [{"message": message}],
                    }
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        upstream = ThreadingHTTPServer(("127.0.0.1", 0), UpstreamHandler)
        thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        thread.start()
        router = CodexProxyServer(
            upstream_base_url=f"http://127.0.0.1:{upstream.server_address[1]}",
            api_key="key",
            model="deepseek-v4-pro",
            proxy=ProxyConfig(),
            capabilities={"tool_call_reasoning_required": True},
        )
        router.start()
        try:
            with httpx.Client(trust_env=False) as client:
                first = client.post(
                    f"{router.base_url}/responses",
                    json={
                        "input": "call a tool",
                        "tools": [
                            {
                                "type": "function",
                                "name": "run",
                                "parameters": {"type": "object"},
                            }
                        ],
                    },
                    timeout=5,
                )
                second = client.post(
                    f"{router.base_url}/responses",
                    json={
                        "previous_response_id": first.json()["id"],
                        "input": [
                            {
                                "type": "function_call_output",
                                "call_id": "call_1",
                                "output": "result",
                            }
                        ],
                    },
                    timeout=5,
                )
            self.assertEqual(second.status_code, 200, second.text)
            self.assertEqual(captured[1]["messages"][0]["role"], "assistant")
            self.assertEqual(
                captured[1]["messages"][0]["tool_calls"][0]["id"],
                "call_1",
            )
            self.assertEqual(
                captured[1]["messages"][0]["reasoning_content"],
                "tool call",
            )
            self.assertEqual(captured[1]["messages"][1]["role"], "tool")
        finally:
            router.stop()
            upstream.shutdown()
            upstream.server_close()
            thread.join(timeout=2)

    def test_streaming_proxy_and_plain_text_error(self) -> None:
        request_count = 0
        captured = []

        class UpstreamHandler(BaseHTTPRequestHandler):
            def log_message(self, _format, *_args):
                return

            def do_POST(self):
                nonlocal request_count
                request_count += 1
                length = int(self.headers["Content-Length"])
                body = json.loads(self.rfile.read(length))
                captured.append(body)
                if request_count == 2:
                    data = b"upstream unavailable"
                    self.send_response(503)
                    self.send_header("Content-Type", "text/plain")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                chunks = [
                    {
                        "choices": [
                            {"delta": {"reasoning_content": "why"}}
                        ]
                    },
                    {"choices": [{"delta": {"content": "answer"}}]},
                    {
                        "choices": [{"finish_reason": "stop", "delta": {}}],
                        "usage": {
                            "prompt_tokens": 1,
                            "completion_tokens": 2,
                            "total_tokens": 3,
                        },
                    },
                ]
                data = "".join(
                    f"data: {json.dumps(chunk)}\n\n" for chunk in chunks
                ) + "data: [DONE]\n\n"
                encoded = data.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

        upstream = ThreadingHTTPServer(("127.0.0.1", 0), UpstreamHandler)
        thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        thread.start()
        router = CodexProxyServer(
            upstream_base_url=f"http://127.0.0.1:{upstream.server_address[1]}",
            api_key="key",
            model="glm-5.1",
            proxy=ProxyConfig(),
        )
        router.start()
        try:
            with httpx.Client(trust_env=False) as client:
                stream = client.post(
                    f"{router.base_url}/responses",
                    json={"input": "ping", "stream": True},
                    timeout=5,
                )
                error = client.post(
                    f"{router.base_url}/responses",
                    json={"input": "ping"},
                    timeout=5,
                )
            self.assertEqual(stream.status_code, 200, stream.text)
            self.assertIn("response.created", stream.text)
            self.assertIn("response.in_progress", stream.text)
            self.assertIn("response.reasoning_summary_text.delta", stream.text)
            self.assertIn("response.output_text.delta", stream.text)
            self.assertIn("response.completed", stream.text)
            self.assertTrue(captured[0]["stream"])
            self.assertEqual(error.status_code, 503)
            self.assertEqual(
                error.json()["error"]["message"],
                "upstream unavailable",
            )
            self.assertEqual(error.json()["error"]["status_code"], 503)
        finally:
            router.stop()
            upstream.shutdown()
            upstream.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
