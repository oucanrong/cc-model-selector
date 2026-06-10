# 路径: src/services/codex_responses_protocol.py
# 作用: Codex Responses 请求与方舟 Responses API 的工具和推理兼容

from __future__ import annotations

from copy import deepcopy
import json
import re
from typing import Any

from src.core.constants import (
    CODEX_REASONING_CONTROL_EFFORT,
    CODEX_REASONING_CONTROL_NONE,
    CODEX_REASONING_CONTROL_TOGGLE,
)


def _flat_name(namespace: str, name: str) -> str:
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


def _function_tool(
    tool: dict[str, Any],
    registry: dict[str, dict[str, str]],
    namespace: str = "",
) -> dict[str, Any] | None:
    tool_type = str(tool.get("type") or "function")
    name = str(tool.get("name") or "")
    if tool_type == "tool_search":
        name = "tool_search"
    if not name:
        return None
    flat_name = _flat_name(namespace, name)
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
        "name": flat_name,
        "description": str(tool.get("description") or ""),
        "parameters": parameters,
    }


def _convert_tools(
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
                    converted = _function_tool(child, registry, namespace)
                    if converted:
                        result.append(converted)
            continue
        converted = _function_tool(
            tool,
            registry,
            str(tool.get("namespace") or ""),
        )
        if converted:
            result.append(converted)
    return result


def _convert_tool_choice(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    choice_type = str(value.get("type") or "")
    if choice_type not in {"custom", "function", "tool_search"}:
        return deepcopy(value)
    name = "tool_search" if choice_type == "tool_search" else str(
        value.get("name") or ""
    )
    return {
        "type": "function",
        "name": _flat_name(str(value.get("namespace") or ""), name),
    }


def _convert_input(value: Any) -> Any:
    if not isinstance(value, list):
        return deepcopy(value)
    result: list[Any] = []
    for item in value:
        if not isinstance(item, dict):
            result.append(deepcopy(item))
            continue
        converted = deepcopy(item)
        item_type = str(converted.get("type") or "")
        if item_type in {"custom_tool_call", "tool_search_call"}:
            name = "tool_search" if item_type == "tool_search_call" else str(
                converted.get("name") or ""
            )
            arguments: Any = converted.get("arguments", {})
            if item_type == "custom_tool_call":
                arguments = {"input": converted.pop("input", "")}
            converted["type"] = "function_call"
            converted["name"] = _flat_name(
                str(converted.pop("namespace", "") or ""),
                name,
            )
            converted["arguments"] = json.dumps(
                arguments,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        elif item_type in {"custom_tool_call_output", "tool_search_output"}:
            converted["type"] = "function_call_output"
        result.append(converted)
    return result


def prepare_ark_request(
    body: dict[str, Any],
    model: str,
    reasoning_control: str,
    reasoning_effort: str,
    thinking_enabled: bool,
) -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    result = deepcopy(body)
    result["model"] = model
    registry: dict[str, dict[str, str]] = {}
    if "tools" in result:
        result["tools"] = _convert_tools(result["tools"], registry)
    if "tool_choice" in result:
        result["tool_choice"] = _convert_tool_choice(result["tool_choice"])
    if "input" in result:
        result["input"] = _convert_input(result["input"])

    if reasoning_control == CODEX_REASONING_CONTROL_EFFORT:
        reasoning = result.get("reasoning")
        effort = (
            str(reasoning.get("effort") or "")
            if isinstance(reasoning, dict)
            else ""
        ) or reasoning_effort
        if effort not in {"minimal", "low", "medium", "high"}:
            effort = "medium"
        result["thinking"] = {
            "type": "disabled" if effort == "minimal" else "enabled"
        }
        result["reasoning"] = {
            **(reasoning if isinstance(reasoning, dict) else {}),
            "effort": effort,
        }
    elif reasoning_control == CODEX_REASONING_CONTROL_TOGGLE:
        result["thinking"] = {
            "type": "enabled" if thinking_enabled else "disabled"
        }
        result.pop("reasoning", None)
    elif reasoning_control == CODEX_REASONING_CONTROL_NONE:
        result.pop("thinking", None)
        result.pop("reasoning", None)
    return result, registry


def _tool_item(
    item: dict[str, Any],
    registry: dict[str, dict[str, str]],
) -> dict[str, Any]:
    if item.get("type") != "function_call":
        return deepcopy(item)
    result = deepcopy(item)
    flat_name = str(result.get("name") or "")
    metadata = registry.get(flat_name)
    if not metadata:
        return result
    result["name"] = metadata["name"]
    namespace = metadata.get("namespace")
    if namespace:
        result["namespace"] = namespace
    if metadata["type"] == "custom":
        arguments = result.pop("arguments", "{}")
        try:
            parsed = json.loads(arguments)
        except (TypeError, json.JSONDecodeError):
            parsed = {}
        result["type"] = "custom_tool_call"
        result["input"] = (
            parsed.get("input", "") if isinstance(parsed, dict) else ""
        )
    elif metadata["type"] == "tool_search":
        arguments = result.get("arguments", "{}")
        try:
            parsed = json.loads(arguments)
        except (TypeError, json.JSONDecodeError):
            parsed = {"query": str(arguments)}
        result["type"] = "tool_search_call"
        result["execution"] = "client"
        result["arguments"] = parsed
    return result


def convert_ark_response(
    body: dict[str, Any],
    registry: dict[str, dict[str, str]],
) -> dict[str, Any]:
    result = deepcopy(body)
    output = result.get("output")
    if isinstance(output, list):
        result["output"] = [
            _tool_item(item, registry) if isinstance(item, dict) else item
            for item in output
        ]
    return result


class ArkResponsesEventConverter:
    def __init__(self, registry: dict[str, dict[str, str]]) -> None:
        self.registry = registry
        self.arguments: dict[str, str] = {}
        self.item_tools: dict[str, dict[str, str]] = {}

    def convert(self, event: dict[str, Any]) -> dict[str, Any] | None:
        result = deepcopy(event)
        event_type = str(result.get("type") or "")
        item = result.get("item")
        if isinstance(item, dict) and item.get("type") == "function_call":
            item_id = str(item.get("id") or "")
            metadata = self.registry.get(str(item.get("name") or ""))
            if item_id and metadata:
                self.item_tools[item_id] = metadata
            result["item"] = _tool_item(item, self.registry)
        if event_type == "response.function_call_arguments.delta":
            item_id = str(result.get("item_id") or "")
            name = self._name_for_item(item_id)
            if not name:
                return result
            self.arguments[item_id] = self.arguments.get(item_id, "") + str(
                result.get("delta") or ""
            )
            return None
        if event_type == "response.function_call_arguments.done":
            item_id = str(result.get("item_id") or "")
            name = self._name_for_item(item_id)
            if not name:
                return result
            raw = str(result.get("arguments") or self.arguments.get(item_id, ""))
            result["type"] = "response.custom_tool_call_input.done"
            result.pop("arguments", None)
            result["input"] = self._custom_input(raw)
        response = result.get("response")
        if isinstance(response, dict):
            result["response"] = convert_ark_response(response, self.registry)
        return result

    def _name_for_item(self, item_id: str) -> str:
        metadata = self.item_tools.get(item_id)
        if metadata and metadata.get("type") == "custom":
            return metadata["name"]
        return ""

    @staticmethod
    def _custom_input(arguments: str) -> str:
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError:
            return arguments
        if isinstance(parsed, dict):
            return str(parsed.get("input") or "")
        return arguments
