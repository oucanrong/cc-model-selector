# 路径: src/services/codex_proxy_server.py
# 作用: 绑定随机本地端口，将 Codex Responses 请求转换并转发到 Chat Completions

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

import httpx

from src.core.config_manager import ProxyConfig
from src.services.codex_protocol import (
    ChatStreamToResponses,
    ResponseHistoryCache,
    chat_to_response,
    iter_sse_json,
    normalize_error,
    responses_to_chat,
)
from src.services.proxy_service import build_proxy_env


class CodexProxyServer:
    def __init__(
        self,
        upstream_base_url: str,
        api_key: str,
        model: str,
        proxy: ProxyConfig,
        capabilities: dict[str, Any] | None = None,
        log: Callable[[str], None] | None = None,
    ) -> None:
        self.upstream_base_url = upstream_base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.proxy = proxy
        self.capabilities = capabilities or {}
        self.log = log or (lambda _message: None)
        self.history = ResponseHistoryCache(max_entries=512)
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        if self._server is None:
            raise RuntimeError("转换服务器尚未启动。")
        return int(self._server.server_address[1])

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1"

    def start(self) -> None:
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, _format: str, *_args: Any) -> None:
                return

            def do_GET(self) -> None:
                if self.path.rstrip("/") in {"", "/health", "/v1/health"}:
                    self._send_json(200, {"status": "ok"})
                else:
                    self._send_json(404, {"error": {"message": "Not found"}})

            def do_POST(self) -> None:
                path = self.path.split("?", 1)[0].rstrip("/")
                if path not in {
                    "/responses",
                    "/v1/responses",
                    "/responses/compact",
                    "/v1/responses/compact",
                }:
                    self._send_json(404, {"error": {"message": "Not found"}})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    body = json.loads(self.rfile.read(length) or b"{}")
                    owner._forward(self, body)
                except Exception as exc:
                    owner.log(f"[ROUTER-ERROR] {exc}")
                    status = 400 if isinstance(exc, ValueError) else 502
                    self._send_json(status, normalize_error(str(exc), status))

            def _send_json(self, status: int, value: dict[str, Any]) -> None:
                data = json.dumps(value, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(data)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="codex-protocol-router",
            daemon=True,
        )
        self._thread.start()
        self.log(f"[ROUTER] 本地转换服务已启动：{self.base_url}")

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=3)
        self._server = None
        self._thread = None
        self.history.clear()

    def _client(self) -> httpx.Client:
        proxy_env = build_proxy_env(self.proxy)
        socks_proxy = proxy_env.get("ALL_PROXY")
        if socks_proxy:
            return httpx.Client(proxy=socks_proxy, timeout=300, trust_env=False)
        mounts: dict[str, httpx.HTTPTransport] = {}
        if proxy_env.get("HTTP_PROXY"):
            mounts["http://"] = httpx.HTTPTransport(proxy=proxy_env["HTTP_PROXY"])
        if proxy_env.get("HTTPS_PROXY"):
            mounts["https://"] = httpx.HTTPTransport(proxy=proxy_env["HTTPS_PROXY"])
        return httpx.Client(mounts=mounts, timeout=300, trust_env=False)

    def _chat_url(self) -> str:
        if self.upstream_base_url.endswith("/chat/completions"):
            return self.upstream_base_url
        return f"{self.upstream_base_url}/chat/completions"

    def _forward(self, handler: BaseHTTPRequestHandler, body: dict[str, Any]) -> None:
        call_ids = [
            str(item.get("call_id") or "")
            for item in body.get("input", [])
            if isinstance(item, dict)
            and item.get("type") in {
                "function_call_output",
                "custom_tool_call_output",
                "tool_search_output",
            }
            and item.get("call_id")
        ]
        restored_calls = self.history.restore(
            body.get("previous_response_id"),
            call_ids,
        )
        tool_registry: dict[str, dict[str, str]] = {}
        chat_body = responses_to_chat(
            body,
            self.model,
            capabilities=self.capabilities,
            tool_registry=tool_registry,
            restored_calls=restored_calls,
        )
        headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream" if chat_body["stream"] else "application/json",
        }
        self.log(f"[ROUTER] POST {self._chat_url()} model={self.model}")
        with self._client() as client:
            if not chat_body["stream"]:
                response = client.post(self._chat_url(), json=chat_body, headers=headers)
                if response.is_error:
                    self._relay_error(handler, response)
                    return
                try:
                    upstream = response.json()
                except json.JSONDecodeError:
                    self._send_error(
                        handler,
                        502,
                        normalize_error(response.content, 502),
                    )
                    return
                converted = chat_to_response(
                    upstream,
                    self.model,
                    tool_registry=tool_registry,
                    capabilities=self.capabilities,
                )
                self.history.store(converted["id"], converted["output"])
                data = json.dumps(converted, ensure_ascii=False).encode("utf-8")
                handler.send_response(response.status_code)
                handler.send_header("Content-Type", "application/json; charset=utf-8")
                handler.send_header("Content-Length", str(len(data)))
                handler.send_header("Connection", "close")
                handler.end_headers()
                handler.wfile.write(data)
                return

            with client.stream(
                "POST",
                self._chat_url(),
                json=chat_body,
                headers=headers,
            ) as response:
                if response.is_error:
                    response.read()
                    self._relay_error(handler, response)
                    return
                handler.send_response(response.status_code)
                handler.send_header("Content-Type", "text/event-stream; charset=utf-8")
                handler.send_header("Cache-Control", "no-cache")
                handler.send_header("Connection", "close")
                handler.end_headers()
                converter = ChatStreamToResponses(
                    self.model,
                    tool_registry=tool_registry,
                    capabilities=self.capabilities,
                )
                for event in converter.start_events():
                    handler.wfile.write(event)
                    handler.wfile.flush()
                try:
                    for chunk in iter_sse_json(response.iter_lines()):
                        for event in converter.feed(chunk):
                            handler.wfile.write(event)
                            handler.wfile.flush()
                        if converter.failed:
                            break
                    if converter.failed:
                        handler.wfile.write(b"data: [DONE]\n\n")
                        handler.wfile.flush()
                        return
                    for event in converter.finish_events():
                        handler.wfile.write(event)
                        handler.wfile.flush()
                    completed = converter.completed_response()
                    self.history.store(completed["id"], completed["output"])
                except Exception as exc:
                    handler.wfile.write(
                        converter.failed_event(normalize_error(str(exc), 502))
                    )
                    handler.wfile.write(b"data: [DONE]\n\n")
                    handler.wfile.flush()

    @staticmethod
    def _relay_error(handler: BaseHTTPRequestHandler, response: httpx.Response) -> None:
        try:
            value: Any = response.json()
        except json.JSONDecodeError:
            value = response.content
        CodexProxyServer._send_error(
            handler,
            response.status_code,
            normalize_error(value, response.status_code),
        )

    @staticmethod
    def _send_error(
        handler: BaseHTTPRequestHandler,
        status_code: int,
        value: dict[str, Any],
    ) -> None:
        data = json.dumps(value, ensure_ascii=False).encode("utf-8")
        handler.send_response(status_code)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(data)))
        handler.send_header("Connection", "close")
        handler.end_headers()
        handler.wfile.write(data)
