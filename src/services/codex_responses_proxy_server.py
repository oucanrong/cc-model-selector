# 路径: src/services/codex_responses_proxy_server.py
# 作用: 转发方舟 Responses API，并兼容 Codex custom/freeform 工具

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

import httpx

from src.core.config_manager import ProxyConfig
from src.services.codex_protocol import normalize_error
from src.services.codex_responses_protocol import (
    ArkResponsesEventConverter,
    convert_ark_response,
    prepare_ark_request,
)
from src.services.proxy_service import build_proxy_env


class CodexResponsesProxyServer:
    def __init__(
        self,
        upstream_base_url: str,
        api_key: str,
        model: str,
        proxy: ProxyConfig,
        reasoning_control: str,
        reasoning_effort: str,
        thinking_enabled: bool,
        log: Callable[[str], None] | None = None,
    ) -> None:
        self.upstream_base_url = upstream_base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.proxy = proxy
        self.reasoning_control = reasoning_control
        self.reasoning_effort = reasoning_effort
        self.thinking_enabled = thinking_enabled
        self.log = log or (lambda _message: None)
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
                    owner._forward(self, body, path)
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
            name="codex-ark-responses-router",
            daemon=True,
        )
        self._thread.start()
        self.log(f"[ROUTER] 方舟 Responses 兼容服务已启动：{self.base_url}")

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=3)
        self._server = None
        self._thread = None

    def _client(self) -> httpx.Client:
        proxy_env = build_proxy_env(self.proxy)
        socks_proxy = proxy_env.get("ALL_PROXY")
        if socks_proxy:
            return httpx.Client(proxy=socks_proxy, timeout=300, trust_env=False)
        mounts: dict[str, httpx.HTTPTransport] = {}
        if proxy_env.get("HTTP_PROXY"):
            mounts["http://"] = httpx.HTTPTransport(proxy=proxy_env["HTTP_PROXY"])
        if proxy_env.get("HTTPS_PROXY"):
            mounts["https://"] = httpx.HTTPTransport(
                proxy=proxy_env["HTTPS_PROXY"]
            )
        return httpx.Client(mounts=mounts, timeout=300, trust_env=False)

    def _responses_url(self, local_path: str) -> str:
        suffix = "/responses"
        if self.upstream_base_url.endswith(suffix):
            return self.upstream_base_url
        return f"{self.upstream_base_url}{suffix}"

    def _forward(
        self,
        handler: BaseHTTPRequestHandler,
        body: dict[str, Any],
        local_path: str,
    ) -> None:
        request_body, registry = prepare_ark_request(
            body,
            self.model,
            self.reasoning_control,
            self.reasoning_effort,
            self.thinking_enabled,
        )
        url = self._responses_url(local_path)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": (
                "text/event-stream"
                if request_body.get("stream")
                else "application/json"
            ),
        }
        self.log(f"[ROUTER] POST {url} model={self.model}")
        with self._client() as client:
            if not request_body.get("stream"):
                response = client.post(url, json=request_body, headers=headers)
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
                converted = convert_ark_response(upstream, registry)
                data = json.dumps(converted, ensure_ascii=False).encode("utf-8")
                handler.send_response(response.status_code)
                handler.send_header(
                    "Content-Type",
                    "application/json; charset=utf-8",
                )
                handler.send_header("Content-Length", str(len(data)))
                handler.send_header("Connection", "close")
                handler.end_headers()
                handler.wfile.write(data)
                return

            with client.stream(
                "POST",
                url,
                json=request_body,
                headers=headers,
            ) as response:
                if response.is_error:
                    response.read()
                    self._relay_error(handler, response)
                    return
                handler.send_response(response.status_code)
                handler.send_header(
                    "Content-Type",
                    "text/event-stream; charset=utf-8",
                )
                handler.send_header("Cache-Control", "no-cache")
                handler.send_header("Connection", "close")
                handler.end_headers()
                converter = ArkResponsesEventConverter(registry)
                for line in response.iter_lines():
                    if not line:
                        continue
                    if line == "data: [DONE]":
                        handler.wfile.write(b"data: [DONE]\n\n")
                        handler.wfile.flush()
                        continue
                    if not line.startswith("data:"):
                        continue
                    payload = json.loads(line[5:].strip())
                    converted = converter.convert(payload)
                    if converted is None:
                        continue
                    event_type = str(converted.get("type") or "")
                    encoded = json.dumps(
                        converted,
                        ensure_ascii=False,
                    ).encode("utf-8")
                    if event_type:
                        handler.wfile.write(f"event: {event_type}\n".encode())
                    handler.wfile.write(b"data: " + encoded + b"\n\n")
                    handler.wfile.flush()

    @staticmethod
    def _relay_error(
        handler: BaseHTTPRequestHandler,
        response: httpx.Response,
    ) -> None:
        try:
            value: Any = response.json()
        except json.JSONDecodeError:
            value = response.content
        CodexResponsesProxyServer._send_error(
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
