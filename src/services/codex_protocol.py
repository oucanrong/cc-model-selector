# 路径: src/services/codex_protocol.py
# 作用: OpenAI Responses API 与 Chat Completions API 的协议转换

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
import json
import re
import threading
import time
import uuid
from typing import Any, Iterable


_DISABLED_EFFORTS = {"none", "off", "disabled"}
_PASSTHROUGH_PARAMS = {
    "frequency_penalty",
    "logit_bias",
    "logprobs",
    "metadata",
    "n",
    "parallel_tool_calls",
    "presence_penalty",
    "seed",
    "service_tier",
    "stop",
    "store",
    "top_logprobs",
    "user",
}


def _compact_json(value: Any) -> str:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return value
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    chunks: list[str] = []
    for part in content:
        if isinstance(part, str):
            chunks.append(part)
        elif isinstance(part, dict):
            for key in ("text", "refusal", "content"):
                value = part.get(key)
                if isinstance(value, str) and value:
                    chunks.append(value)
                    break
    return "\n".join(chunks)


def _image_part(part: dict[str, Any]) -> dict[str, Any] | None:
    url = part.get("image_url") or part.get("url")
    if isinstance(url, dict):
        url = url.get("url")
    if not isinstance(url, str) or not url:
        return None
    result: dict[str, Any] = {"type": "image_url", "image_url": {"url": url}}
    detail = part.get("detail")
    if isinstance(detail, str) and detail:
        result["image_url"]["detail"] = detail
    return result


def _chat_content(content: Any) -> str | list[dict[str, Any]]:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[dict[str, Any]] = []
    for part in content:
        if isinstance(part, str):
            parts.append({"type": "text", "text": part})
        elif isinstance(part, dict):
            if part.get("type") == "input_image":
                image = _image_part(part)
                if image:
                    parts.append(image)
            else:
                text = _text_from_content([part])
                if text:
                    parts.append({"type": "text", "text": text})
    if not any(part.get("type") == "image_url" for part in parts):
        return "\n".join(
            str(part.get("text", ""))
            for part in parts
            if part.get("type") == "text"
        )
    return parts


def _flatten_tool_name(namespace: str, name: str) -> str:
    raw = f"{namespace}__{name}" if namespace else name
    return re.sub(r"[^A-Za-z0-9_-]", "_", raw)[:64]


def _schema(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return deepcopy(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return parsed
    return {"type": "object", "properties": {}}


def _register_tool(
    tool: dict[str, Any],
    registry: dict[str, dict[str, str]],
    namespace: str = "",
) -> dict[str, Any] | None:
    tool_type = str(tool.get("type") or "function")
    name = tool.get("name")
    if tool_type == "tool_search":
        name = "tool_search"
    if not isinstance(name, str) or not name:
        return None
    flat_name = _flatten_tool_name(namespace, name)
    registry[flat_name] = {
        "type": tool_type,
        "name": name,
        "namespace": namespace,
    }
    if tool_type == "custom":
        parameters = {
            "type": "object",
            "properties": {"input": {"type": "string"}},
            "required": ["input"],
        }
    elif tool_type == "tool_search":
        parameters = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        }
    else:
        parameters = _schema(tool.get("parameters") or tool.get("input_schema"))
    return {
        "type": "function",
        "function": {
            "name": flat_name,
            "description": str(tool.get("description") or ""),
            "parameters": parameters,
        },
    }


def _chat_tools(
    tools: Any,
    registry: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if not isinstance(tools, list):
        return result
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        if tool.get("type") == "namespace":
            namespace = str(tool.get("name") or tool.get("namespace") or "")
            for child in tool.get("tools") or []:
                if isinstance(child, dict):
                    converted = _register_tool(child, registry, namespace)
                    if converted:
                        result.append(converted)
            continue
        namespace = str(tool.get("namespace") or "")
        converted = _register_tool(tool, registry, namespace)
        if converted:
            result.append(converted)
    return result


def _collapse_system_messages(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    system: list[str] = []
    rest: list[dict[str, Any]] = []
    for message in messages:
        if message.get("role") == "system":
            text = _text_from_content(message.get("content"))
            if text:
                system.append(text)
        else:
            rest.append(message)
    if system:
        return [{"role": "system", "content": "\n\n".join(system)}, *rest]
    return rest


def _apply_reasoning(
    result: dict[str, Any],
    reasoning: Any,
    capabilities: dict[str, Any],
) -> None:
    if "thinking_enabled" in capabilities:
        enabled = bool(capabilities["thinking_enabled"])
        thinking_param = str(capabilities.get("thinking_param") or "")
        if thinking_param == "thinking":
            result["thinking"] = {
                "type": "enabled" if enabled else "disabled"
            }
        elif thinking_param in {"enable_thinking", "reasoning_split"}:
            result[thinking_param] = enabled
        return
    if not isinstance(reasoning, dict):
        return
    effort = reasoning.get("effort")
    enabled = str(effort).lower() not in _DISABLED_EFFORTS
    thinking_param = str(capabilities.get("thinking_param") or "")
    if thinking_param == "thinking":
        result["thinking"] = {"type": "enabled" if enabled else "disabled"}
    elif thinking_param in {"enable_thinking", "reasoning_split"}:
        result[thinking_param] = enabled
    effort_param = str(capabilities.get("effort_param") or "")
    if not enabled or not effort or not effort_param:
        return
    mapped = capabilities.get("effort_map", {}).get(effort, effort)
    if effort_param == "reasoning.effort":
        result["reasoning"] = {"effort": mapped}
    else:
        result[effort_param] = mapped


def responses_to_chat(
    body: dict[str, Any],
    model: str,
    capabilities: dict[str, Any] | None = None,
    tool_registry: dict[str, dict[str, str]] | None = None,
    restored_calls: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    capabilities = capabilities or {
        "thinking_param": "thinking",
        "effort_param": (
            "reasoning_effort" if model.lower().startswith("deepseek-") else ""
        ),
        "effort_map": {
            "low": "high",
            "medium": "high",
            "xhigh": "max",
        },
    }
    registry = tool_registry if tool_registry is not None else {}
    messages: list[dict[str, Any]] = []
    instructions = _text_from_content(body.get("instructions"))
    if instructions:
        messages.append({"role": "system", "content": instructions})
    if restored_calls:
        messages.append(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": deepcopy(restored_calls),
            }
        )

    input_value = body.get("input", [])
    if isinstance(input_value, str):
        messages.append({"role": "user", "content": input_value})
    elif isinstance(input_value, list):
        pending_calls: list[dict[str, Any]] = []
        pending_reasoning = ""

        def flush_pending_calls() -> None:
            nonlocal pending_calls, pending_reasoning
            if not pending_calls:
                return
            message: dict[str, Any] = {
                "role": "assistant",
                "content": None,
                "tool_calls": pending_calls,
            }
            if pending_reasoning:
                message["reasoning_content"] = pending_reasoning
            messages.append(message)
            pending_calls = []
            pending_reasoning = ""

        for item in input_value:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            if item_type == "message":
                role = str(item.get("role") or "user")
                if role == "developer":
                    role = "system"
                message: dict[str, Any] = {
                    "role": role,
                    "content": _chat_content(item.get("content")),
                }
                refusal = item.get("refusal")
                if isinstance(refusal, str) and refusal:
                    message["refusal"] = refusal
                messages.append(message)
            elif item_type in {
                "function_call",
                "custom_tool_call",
                "tool_search_call",
            }:
                original_name = str(item.get("name") or "")
                namespace = str(item.get("namespace") or "")
                name = _flatten_tool_name(namespace, original_name)
                if item_type == "tool_search_call":
                    name = "tool_search"
                arguments = item.get("arguments", "{}")
                if item_type == "custom_tool_call":
                    arguments = {"input": item.get("input", "")}
                pending_calls.append(
                    {
                        "id": item.get("call_id")
                        or item.get("id")
                        or f"call_{uuid.uuid4().hex}",
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": _compact_json(arguments),
                        },
                    }
                )
                item_reasoning = extract_reasoning(item)
                if item_reasoning:
                    pending_reasoning += item_reasoning
            elif item_type in {
                "function_call_output",
                "custom_tool_call_output",
                "tool_search_output",
            }:
                flush_pending_calls()
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": str(item.get("call_id") or ""),
                        "content": _text_from_content(item.get("output")),
                    }
                )
        flush_pending_calls()

    if capabilities.get("tool_call_reasoning_required"):
        for message in messages:
            if message.get("role") == "assistant" and message.get("tool_calls"):
                if not message.get("reasoning_content"):
                    message["reasoning_content"] = "tool call"

    result: dict[str, Any] = {
        "model": model,
        "messages": _collapse_system_messages(messages),
        "stream": bool(body.get("stream", False)),
    }
    if result["stream"]:
        result["stream_options"] = {"include_usage": True}

    tools = _chat_tools(body.get("tools"), registry)
    if tools:
        result["tools"] = tools
        choice = body.get("tool_choice")
        if isinstance(choice, dict):
            choice_type = str(choice.get("type") or "")
            if choice_type in {"function", "custom", "tool_search"}:
                name = str(choice.get("name") or "")
                namespace = str(choice.get("namespace") or "")
                if choice_type == "tool_search":
                    name = "tool_search"
                result["tool_choice"] = {
                    "type": "function",
                    "function": {"name": _flatten_tool_name(namespace, name)},
                }
        elif choice is not None:
            result["tool_choice"] = choice

    if "temperature" in body:
        result["temperature"] = body["temperature"]
    if "top_p" in body:
        result["top_p"] = body["top_p"]
    if "max_output_tokens" in body:
        result["max_tokens"] = body["max_output_tokens"]
    for key in _PASSTHROUGH_PARAMS:
        if key in body:
            result[key] = body[key]
    _apply_reasoning(result, body.get("reasoning"), capabilities)
    return result


def _reasoning_details_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("text", "content", "summary"):
            text = value.get(key)
            if isinstance(text, str):
                return text
        return ""
    if isinstance(value, list):
        return "".join(_reasoning_details_text(item) for item in value)
    return ""


def extract_reasoning(value: Any, fields: Iterable[str] | None = None) -> str:
    if not isinstance(value, dict):
        return ""
    for key in fields or ("reasoning_content", "reasoning", "reasoning_details"):
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate:
            return candidate
        if key == "reasoning" and isinstance(candidate, dict):
            text = _reasoning_details_text(candidate)
            if text:
                return text
        if key == "reasoning_details":
            text = _reasoning_details_text(candidate)
            if text:
                return text
    return ""


def _split_inline_think(content: str) -> tuple[str, str]:
    reasoning: list[str] = []

    def replace(match: re.Match[str]) -> str:
        reasoning.append(match.group(1))
        return ""

    text = re.sub(
        r"<think>(.*?)</think>",
        replace,
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not reasoning and content.lower().startswith("<think>"):
        reasoning.append(content[7:])
        text = ""
    return "".join(reasoning), text


def _usage(usage: Any) -> dict[str, Any]:
    usage = usage if isinstance(usage, dict) else {}
    prompt_details = usage.get("prompt_tokens_details") or {}
    completion_details = usage.get("completion_tokens_details") or {}
    input_details: dict[str, Any] = {}
    output_details: dict[str, Any] = {}
    cached = prompt_details.get("cached_tokens", usage.get("cached_tokens"))
    reasoning = completion_details.get(
        "reasoning_tokens",
        usage.get("reasoning_tokens"),
    )
    if cached is not None:
        input_details["cached_tokens"] = cached
    if reasoning is not None:
        output_details["reasoning_tokens"] = reasoning
    result: dict[str, Any] = {
        "input_tokens": usage.get("prompt_tokens", usage.get("input_tokens", 0)),
        "output_tokens": usage.get(
            "completion_tokens",
            usage.get("output_tokens", 0),
        ),
        "total_tokens": usage.get("total_tokens", 0),
    }
    if input_details:
        result["input_tokens_details"] = input_details
    if output_details:
        result["output_tokens_details"] = output_details
    return result


def _tool_item(
    call: dict[str, Any],
    registry: dict[str, dict[str, str]],
) -> dict[str, Any]:
    function = call.get("function") or {}
    flat_name = str(function.get("name") or "")
    metadata = registry.get(flat_name, {})
    tool_type = metadata.get("type", "function")
    name = metadata.get("name", flat_name)
    namespace = metadata.get("namespace", "")
    arguments = _compact_json(function.get("arguments", "{}"))
    call_id = str(call.get("id") or f"call_{uuid.uuid4().hex}")
    if tool_type == "custom":
        try:
            parsed = json.loads(arguments)
            input_value = parsed.get("input", "") if isinstance(parsed, dict) else arguments
        except json.JSONDecodeError:
            input_value = arguments
        item = {
            "id": f"ctc_{uuid.uuid4().hex}",
            "type": "custom_tool_call",
            "status": "completed",
            "call_id": call_id,
            "name": name,
            "input": input_value,
        }
    elif tool_type == "tool_search" or flat_name == "tool_search":
        try:
            parsed_arguments = json.loads(arguments)
        except json.JSONDecodeError:
            parsed_arguments = {"query": arguments}
        item = {
            "id": f"tsc_{uuid.uuid4().hex}",
            "type": "tool_search_call",
            "status": "completed",
            "execution": "client",
            "call_id": call_id,
            "arguments": parsed_arguments,
        }
    else:
        item = {
            "id": f"fc_{uuid.uuid4().hex}",
            "type": "function_call",
            "status": "completed",
            "call_id": call_id,
            "name": name,
            "arguments": arguments,
        }
    if namespace:
        item["namespace"] = namespace
    return item


def chat_to_response(
    body: dict[str, Any],
    model: str,
    custom_tools: set[str] | None = None,
    tool_registry: dict[str, dict[str, str]] | None = None,
    capabilities: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registry = dict(tool_registry or {})
    for name in custom_tools or set():
        registry.setdefault(name, {"type": "custom", "name": name, "namespace": ""})
    response_id = str(body.get("id") or f"resp_{uuid.uuid4().hex}")
    choice = (body.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    output: list[dict[str, Any]] = []
    fields = (capabilities or {}).get("response_fields")
    reasoning = extract_reasoning(message, fields)
    content = message.get("content")
    if isinstance(content, list):
        content = _text_from_content(content)
    if isinstance(content, str):
        inline_reasoning, content = _split_inline_think(content)
        if not reasoning:
            reasoning = inline_reasoning
    if reasoning:
        output.append(
            {
                "id": f"rs_{uuid.uuid4().hex}",
                "type": "reasoning",
                "summary": [{"type": "summary_text", "text": reasoning}],
            }
        )
    refusal = message.get("refusal")
    content_parts: list[dict[str, Any]] = []
    if isinstance(content, str) and content:
        content_parts.append(
            {"type": "output_text", "text": content, "annotations": []}
        )
    if isinstance(refusal, str) and refusal:
        content_parts.append({"type": "refusal", "refusal": refusal})
    if content_parts:
        output.append(
            {
                "id": f"msg_{uuid.uuid4().hex}",
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": content_parts,
            }
        )
    for call in message.get("tool_calls") or []:
        if isinstance(call, dict):
            output.append(_tool_item(call, registry))

    finish_reason = choice.get("finish_reason")
    status = "incomplete" if finish_reason == "length" else "completed"
    result: dict[str, Any] = {
        "id": response_id,
        "object": "response",
        "created_at": body.get("created") or int(time.time()),
        "status": status,
        "model": body.get("model") or model,
        "output": output,
        "usage": _usage(body.get("usage")),
    }
    if status == "incomplete":
        result["incomplete_details"] = {"reason": "max_output_tokens"}
    return result


class ResponseHistoryCache:
    def __init__(self, max_entries: int = 512) -> None:
        self.max_entries = max_entries
        self._responses: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
        self._call_to_responses: dict[str, set[str]] = {}
        self._lock = threading.RLock()

    def store(self, response_id: str, output: Iterable[dict[str, Any]]) -> None:
        calls: list[dict[str, Any]] = []
        for item in output:
            if item.get("type") not in {
                "function_call",
                "custom_tool_call",
                "tool_search_call",
            }:
                continue
            name = str(item.get("name") or "")
            if item.get("type") == "tool_search_call":
                name = "tool_search"
            arguments: Any = item.get("arguments", "{}")
            if item.get("type") == "custom_tool_call":
                arguments = {"input": item.get("input", "")}
            calls.append(
                {
                    "id": str(item.get("call_id") or item.get("id") or ""),
                    "type": "function",
                    "function": {
                        "name": name,
                        "arguments": _compact_json(arguments),
                    },
                }
            )
        with self._lock:
            self._remove_locked(response_id)
            self._responses[response_id] = calls
            for call in calls:
                self._call_to_responses.setdefault(call["id"], set()).add(response_id)
            while len(self._responses) > self.max_entries:
                oldest = next(iter(self._responses))
                self._remove_call_indexes_locked(oldest)
                self._responses.pop(oldest, None)

    def restore(
        self,
        previous_response_id: str | None,
        call_ids: Iterable[str],
    ) -> list[dict[str, Any]]:
        with self._lock:
            if previous_response_id:
                calls = self._responses.get(previous_response_id)
                if calls is None:
                    raise ValueError("previous_response_id 不存在或已过期。")
                self._responses.move_to_end(previous_response_id)
                return deepcopy(calls)
            matched: set[str] = set()
            for call_id in call_ids:
                matched.update(self._call_to_responses.get(call_id, set()))
            if len(matched) > 1:
                raise ValueError("call_id 对应多个历史响应，无法唯一恢复。")
            if len(matched) == 1:
                response_id = next(iter(matched))
                return deepcopy(self._responses.get(response_id, []))
            return []

    def clear(self) -> None:
        with self._lock:
            self._responses.clear()
            self._call_to_responses.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._responses)

    def _remove_locked(self, response_id: str) -> None:
        if response_id in self._responses:
            self._remove_call_indexes_locked(response_id)
            self._responses.pop(response_id)

    def _remove_call_indexes_locked(self, response_id: str) -> None:
        calls = self._responses.get(response_id, [])
        call_ids = {str(call.get("id") or "") for call in calls}
        for call_id in call_ids:
            response_ids = self._call_to_responses.get(call_id, set())
            response_ids.discard(response_id)
            if not response_ids:
                self._call_to_responses.pop(call_id, None)


class _ThinkStreamParser:
    def __init__(self) -> None:
        self.buffer = ""
        self.in_think = False

    def feed(self, text: str, final: bool = False) -> list[tuple[str, str]]:
        self.buffer += text
        result: list[tuple[str, str]] = []
        while self.buffer:
            tag = "</think>" if self.in_think else "<think>"
            lower = self.buffer.lower()
            index = lower.find(tag)
            if index >= 0:
                if index:
                    result.append(
                        ("reasoning" if self.in_think else "text", self.buffer[:index])
                    )
                self.buffer = self.buffer[index + len(tag):]
                self.in_think = not self.in_think
                continue
            if final:
                result.append(
                    ("reasoning" if self.in_think else "text", self.buffer)
                )
                self.buffer = ""
                break
            keep = min(len(tag) - 1, len(self.buffer))
            emit = self.buffer[:-keep] if keep else self.buffer
            if emit:
                result.append(("reasoning" if self.in_think else "text", emit))
                self.buffer = self.buffer[-keep:] if keep else ""
            break
        return result


class ChatStreamToResponses:
    def __init__(
        self,
        model: str,
        custom_tools: set[str] | None = None,
        tool_registry: dict[str, dict[str, str]] | None = None,
        capabilities: dict[str, Any] | None = None,
    ) -> None:
        self.model = model
        self.response_id = f"resp_{uuid.uuid4().hex}"
        self.created_at = int(time.time())
        self.message_id = f"msg_{uuid.uuid4().hex}"
        self.reasoning_id = f"rs_{uuid.uuid4().hex}"
        self.message_text = ""
        self.reasoning_text = ""
        self.message_index: int | None = None
        self.reasoning_index: int | None = None
        self.next_output_index = 0
        self.tool_calls: dict[int, dict[str, Any]] = {}
        self.usage: dict[str, Any] = {}
        self.finish_reason: str | None = None
        self.registry = dict(tool_registry or {})
        for name in custom_tools or set():
            self.registry.setdefault(
                name,
                {"type": "custom", "name": name, "namespace": ""},
            )
        self.capabilities = capabilities or {}
        self.think_parser = _ThinkStreamParser()
        self.failed = False

    @staticmethod
    def _event(event_type: str, **payload: Any) -> bytes:
        data = {"type": event_type, **payload}
        return (
            f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        ).encode("utf-8")

    def _response(self, status: str, output: list[dict[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.response_id,
            "object": "response",
            "created_at": self.created_at,
            "status": status,
            "model": self.model,
            "output": output,
            "usage": _usage(self.usage),
        }
        if status == "incomplete":
            result["incomplete_details"] = {"reason": "max_output_tokens"}
        return result

    def start_events(self) -> list[bytes]:
        response = self._response("in_progress", [])
        return [
            self._event("response.created", response=response),
            self._event("response.in_progress", response=response),
        ]

    def _reasoning_delta(self, text: str) -> list[bytes]:
        if not text:
            return []
        events: list[bytes] = []
        if self.reasoning_index is None:
            self.reasoning_index = self.next_output_index
            self.next_output_index += 1
            events.append(
                self._event(
                    "response.output_item.added",
                    output_index=self.reasoning_index,
                    item={"id": self.reasoning_id, "type": "reasoning", "summary": []},
                )
            )
            events.append(
                self._event(
                    "response.reasoning_summary_part.added",
                    item_id=self.reasoning_id,
                    output_index=self.reasoning_index,
                    summary_index=0,
                    part={"type": "summary_text", "text": ""},
                )
            )
        self.reasoning_text += text
        events.append(
            self._event(
                "response.reasoning_summary_text.delta",
                item_id=self.reasoning_id,
                output_index=self.reasoning_index,
                summary_index=0,
                delta=text,
            )
        )
        return events

    def _text_delta(self, text: str) -> list[bytes]:
        if not text:
            return []
        events: list[bytes] = []
        if self.message_index is None:
            self.message_index = self.next_output_index
            self.next_output_index += 1
            events.append(
                self._event(
                    "response.output_item.added",
                    output_index=self.message_index,
                    item={
                        "id": self.message_id,
                        "type": "message",
                        "status": "in_progress",
                        "role": "assistant",
                        "content": [],
                    },
                )
            )
            events.append(
                self._event(
                    "response.content_part.added",
                    item_id=self.message_id,
                    output_index=self.message_index,
                    content_index=0,
                    part={"type": "output_text", "text": "", "annotations": []},
                )
            )
        self.message_text += text
        events.append(
            self._event(
                "response.output_text.delta",
                item_id=self.message_id,
                output_index=self.message_index,
                content_index=0,
                delta=text,
            )
        )
        return events

    def _tool_delta(self, delta: dict[str, Any]) -> list[bytes]:
        index = int(delta.get("index", 0))
        state = self.tool_calls.setdefault(
            index,
            {
                "id": "",
                "name": "",
                "arguments": "",
                "item_id": f"fc_{uuid.uuid4().hex}",
                "output_index": None,
                "added": False,
            },
        )
        if delta.get("id"):
            state["id"] = str(delta["id"])
        function = delta.get("function") or {}
        name_delta = function.get("name")
        arguments_delta = function.get("arguments")
        if isinstance(name_delta, str):
            state["name"] += name_delta
        events: list[bytes] = []
        if state["name"] and not state["added"]:
            state["added"] = True
            state["output_index"] = self.next_output_index
            self.next_output_index += 1
            metadata = self.registry.get(state["name"], {})
            tool_type = metadata.get("type", "function")
            item_type = "custom_tool_call" if tool_type == "custom" else "function_call"
            item = {
                "id": state["item_id"],
                "type": item_type,
                "status": "in_progress",
                "call_id": state["id"] or f"call_{uuid.uuid4().hex}",
                "name": metadata.get("name", state["name"]),
            }
            item["input" if tool_type == "custom" else "arguments"] = ""
            events.append(
                self._event(
                    "response.output_item.added",
                    output_index=state["output_index"],
                    item=item,
                )
            )
        if isinstance(arguments_delta, str) and arguments_delta:
            state["arguments"] += arguments_delta
            if state["added"]:
                metadata = self.registry.get(state["name"], {})
                event_type = (
                    "response.custom_tool_call_input.delta"
                    if metadata.get("type") == "custom"
                    else "response.function_call_arguments.delta"
                )
                events.append(
                    self._event(
                        event_type,
                        item_id=state["item_id"],
                        output_index=state["output_index"],
                        delta=arguments_delta,
                    )
                )
        return events

    def feed(self, chunk: dict[str, Any]) -> list[bytes]:
        if chunk.get("error"):
            self.failed = True
            return [self.failed_event(normalize_error(chunk))]
        if chunk.get("usage"):
            self.usage = chunk["usage"]
        choices = chunk.get("choices") or []
        if not choices:
            return []
        choice = choices[0]
        if choice.get("finish_reason"):
            self.finish_reason = str(choice["finish_reason"])
        delta = choice.get("delta") or {}
        events: list[bytes] = []
        reasoning = extract_reasoning(
            delta,
            self.capabilities.get("response_fields"),
        )
        if reasoning:
            events.extend(self._reasoning_delta(reasoning))
        content = delta.get("content")
        if isinstance(content, list):
            content = _text_from_content(content)
        if isinstance(content, str) and content:
            for kind, text in self.think_parser.feed(content):
                events.extend(
                    self._reasoning_delta(text)
                    if kind == "reasoning"
                    else self._text_delta(text)
                )
        for tool_delta in delta.get("tool_calls") or []:
            if isinstance(tool_delta, dict):
                events.extend(self._tool_delta(tool_delta))
        return events

    def finish_events(self) -> list[bytes]:
        events: list[bytes] = []
        for kind, text in self.think_parser.feed("", final=True):
            events.extend(
                self._reasoning_delta(text)
                if kind == "reasoning"
                else self._text_delta(text)
            )
        completed: list[tuple[int, dict[str, Any]]] = []
        if self.reasoning_index is not None:
            item = {
                "id": self.reasoning_id,
                "type": "reasoning",
                "summary": [{"type": "summary_text", "text": self.reasoning_text}],
            }
            events.extend(
                [
                    self._event(
                        "response.reasoning_summary_text.done",
                        item_id=self.reasoning_id,
                        output_index=self.reasoning_index,
                        summary_index=0,
                        text=self.reasoning_text,
                    ),
                    self._event(
                        "response.reasoning_summary_part.done",
                        item_id=self.reasoning_id,
                        output_index=self.reasoning_index,
                        summary_index=0,
                        part=item["summary"][0],
                    ),
                    self._event(
                        "response.output_item.done",
                        output_index=self.reasoning_index,
                        item=item,
                    ),
                ]
            )
            completed.append((self.reasoning_index, item))
        if self.message_index is not None:
            part = {
                "type": "output_text",
                "text": self.message_text,
                "annotations": [],
            }
            item = {
                "id": self.message_id,
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [part],
            }
            events.extend(
                [
                    self._event(
                        "response.output_text.done",
                        item_id=self.message_id,
                        output_index=self.message_index,
                        content_index=0,
                        text=self.message_text,
                    ),
                    self._event(
                        "response.content_part.done",
                        item_id=self.message_id,
                        output_index=self.message_index,
                        content_index=0,
                        part=part,
                    ),
                    self._event(
                        "response.output_item.done",
                        output_index=self.message_index,
                        item=item,
                    ),
                ]
            )
            completed.append((self.message_index, item))
        for index in sorted(self.tool_calls):
            state = self.tool_calls[index]
            if not state["added"]:
                fallback_name = state["name"] or "tool"
                state["name"] = ""
                events.extend(
                    self._tool_delta(
                        {"index": index, "function": {"name": fallback_name}}
                    )
                )
            call = {
                "id": state["id"],
                "function": {
                    "name": state["name"],
                    "arguments": state["arguments"],
                },
            }
            item = _tool_item(call, self.registry)
            item["id"] = state["item_id"]
            output_index = int(state["output_index"])
            event_type = (
                "response.custom_tool_call_input.done"
                if item["type"] == "custom_tool_call"
                else "response.function_call_arguments.done"
            )
            value_key = "input" if item["type"] == "custom_tool_call" else "arguments"
            events.append(
                self._event(
                    event_type,
                    item_id=state["item_id"],
                    output_index=output_index,
                    **{value_key: item[value_key]},
                )
            )
            events.append(
                self._event(
                    "response.output_item.done",
                    output_index=output_index,
                    item=item,
                )
            )
            completed.append((output_index, item))
        output = [item for _, item in sorted(completed)]
        status = "incomplete" if self.finish_reason == "length" else "completed"
        event_type = (
            "response.incomplete" if status == "incomplete" else "response.completed"
        )
        events.append(self._event(event_type, response=self._response(status, output)))
        events.append(b"data: [DONE]\n\n")
        return events

    def failed_event(self, error: dict[str, Any]) -> bytes:
        response = self._response("failed", [])
        response["error"] = error["error"]
        return self._event("response.failed", response=response)

    def completed_response(self) -> dict[str, Any]:
        output: list[dict[str, Any]] = []
        if self.reasoning_index is not None:
            output.append(
                {
                    "id": self.reasoning_id,
                    "type": "reasoning",
                    "summary": [
                        {"type": "summary_text", "text": self.reasoning_text}
                    ],
                }
            )
        if self.message_index is not None:
            output.append(
                {
                    "id": self.message_id,
                    "type": "message",
                    "status": "completed",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": self.message_text,
                            "annotations": [],
                        }
                    ],
                }
            )
        for index in sorted(self.tool_calls):
            state = self.tool_calls[index]
            output.append(
                _tool_item(
                    {
                        "id": state["id"],
                        "function": {
                            "name": state["name"],
                            "arguments": state["arguments"],
                        },
                    },
                    self.registry,
                )
            )
        return self._response(
            "incomplete" if self.finish_reason == "length" else "completed",
            output,
        )


def normalize_error(value: Any, status_code: int | None = None) -> dict[str, Any]:
    if isinstance(value, (bytes, bytearray)):
        text = bytes(value).decode("utf-8", errors="replace")
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            value = text
    if isinstance(value, str):
        message = value.strip() or "Upstream request failed"
        error: dict[str, Any] = {"message": message, "type": "upstream_error"}
    elif isinstance(value, dict):
        source = value.get("error")
        if isinstance(source, dict):
            error = dict(source)
        else:
            detail = value.get("detail")
            base_resp = value.get("base_resp")
            if isinstance(detail, dict):
                error = dict(detail)
            elif isinstance(base_resp, dict):
                error = {
                    "message": base_resp.get("status_msg")
                    or base_resp.get("message")
                    or "Upstream request failed",
                    "code": base_resp.get("status_code"),
                    "type": "upstream_error",
                }
            else:
                error = {
                    "message": str(detail or value.get("message") or value),
                    "type": "upstream_error",
                }
    else:
        error = {"message": str(value), "type": "upstream_error"}
    error.setdefault("message", "Upstream request failed")
    error.setdefault("type", "upstream_error")
    if status_code is not None:
        error.setdefault("status_code", status_code)
    return {"error": error}


def iter_sse_json(lines: Iterable[bytes | str]) -> Iterable[dict[str, Any]]:
    buffer = ""
    for raw in lines:
        text = (
            raw.decode("utf-8", errors="replace")
            if isinstance(raw, bytes)
            else raw
        )
        buffer += text
        if "\n" not in buffer:
            buffer += "\n"
        lines_ready = buffer.splitlines(keepends=True)
        buffer = ""
        for line in lines_ready:
            if not line.endswith(("\n", "\r")):
                buffer = line
                continue
            stripped = line.strip()
            if not stripped.startswith("data:"):
                continue
            data = stripped[5:].strip()
            if not data or data == "[DONE]":
                continue
            try:
                value = json.loads(data)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                yield value
