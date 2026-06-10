# 路径: src/services/codex_config_service.py
# 作用: 临时接管并可靠恢复用户的 ~/.codex/config.toml

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import psutil


_MANAGED_PROVIDER_ID = "cc_model_manager"
_STATE_FILE_NAME = "cc-model-manager-config-restore.json"
_CATALOG_FILE_NAME = "cc-model-manager-model-catalog.json"


class CodexConfigService:
    def __init__(
        self,
        config_path: Path | None = None,
        state_path: Path | None = None,
    ) -> None:
        codex_dir = Path.home() / ".codex"
        self.config_path = config_path or codex_dir / "config.toml"
        self.state_path = state_path or codex_dir / _STATE_FILE_NAME
        self.catalog_path = self.config_path.parent / _CATALOG_FILE_NAME
        self._active = False

    def recover_if_needed(self) -> bool:
        if not self.state_path.exists():
            return False
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        owner_pid = state.get("owner_pid")
        if isinstance(owner_pid, int) and psutil.pid_exists(owner_pid):
            return False
        self._restore_from_state()
        return True

    def activate(
        self,
        model: str,
        base_url: str,
        display_name: str | None = None,
        context_window: int = 128_000,
        provider_id: str = _MANAGED_PROVIDER_ID,
        provider_name: str = "CC Model Manager Local Router",
        reasoning_effort: str = "high",
        env_key: str | None = None,
        reasoning_options: tuple[str, ...] | None = None,
        input_modalities: tuple[str, ...] = ("text",),
        effective_context_window_percent: int = 100,
        supports_parallel_tool_calls: bool = False,
        supports_reasoning_summaries: bool | None = None,
    ) -> None:
        if self._active:
            raise RuntimeError("Codex 配置已被当前进程接管。")

        original_exists = self.config_path.exists()
        original_bytes = self.config_path.read_bytes() if original_exists else b""
        catalog_exists = self.catalog_path.exists()
        catalog_bytes = self.catalog_path.read_bytes() if catalog_exists else b""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "config_path": str(self.config_path),
            "owner_pid": os.getpid(),
            "original_exists": original_exists,
            "original_base64": base64.b64encode(original_bytes).decode("ascii"),
            "catalog_path": str(self.catalog_path),
            "catalog_exists": catalog_exists,
            "catalog_base64": base64.b64encode(catalog_bytes).decode("ascii"),
        }
        self.state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        original_text = original_bytes.decode("utf-8-sig", errors="replace")
        catalog = self._build_model_catalog(
            model=model,
            display_name=display_name or model,
            context_window=context_window,
            reasoning_options=reasoning_options,
            reasoning_effort=reasoning_effort,
            input_modalities=input_modalities,
            effective_context_window_percent=effective_context_window_percent,
            supports_parallel_tool_calls=supports_parallel_tool_calls,
            supports_reasoning_summaries=supports_reasoning_summaries,
        )
        self.catalog_path.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        updated = self._inject_managed_config(
            original_text,
            model,
            base_url,
            self.catalog_path,
            provider_id,
            provider_name,
            reasoning_effort,
            context_window,
            env_key,
        )
        self.config_path.write_text(updated, encoding="utf-8")
        self._active = True

    def restore(self) -> None:
        if self._active and self.state_path.exists():
            self._restore_from_state()
        self._active = False

    def _restore_from_state(self) -> None:
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        target = Path(state.get("config_path") or self.config_path)
        original = base64.b64decode(state.get("original_base64", ""))
        if state.get("original_exists", False):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(original)
        elif target.exists():
            target.unlink()
        catalog_target = Path(state.get("catalog_path") or self.catalog_path)
        catalog_original = base64.b64decode(state.get("catalog_base64", ""))
        if state.get("catalog_exists", False):
            catalog_target.parent.mkdir(parents=True, exist_ok=True)
            catalog_target.write_bytes(catalog_original)
        elif catalog_target.exists():
            catalog_target.unlink()
        self.state_path.unlink(missing_ok=True)

    @staticmethod
    def _remove_top_level_keys(text: str, keys: set[str]) -> str:
        result: list[str] = []
        in_table = False
        for line in text.splitlines(keepends=True):
            stripped = line.lstrip()
            if stripped.startswith("["):
                in_table = True
            if not in_table:
                match = re.match(r"^\s*([A-Za-z0-9_-]+)\s*=", line)
                if match and match.group(1) in keys:
                    continue
            result.append(line)
        return "".join(result)

    @staticmethod
    def _remove_table(text: str, table_name: str) -> str:
        lines = text.splitlines(keepends=True)
        result: list[str] = []
        skipping = False
        header = f"[model_providers.{table_name}]"
        for line in lines:
            stripped = line.strip()
            if stripped == header:
                skipping = True
                continue
            if skipping and stripped.startswith("[") and stripped.endswith("]"):
                skipping = False
            if not skipping:
                result.append(line)
        return "".join(result)

    def _inject_managed_config(
        self,
        text: str,
        model: str,
        base_url: str,
        catalog_path: Path,
        provider_id: str,
        provider_name: str,
        reasoning_effort: str,
        context_window: int,
        env_key: str | None,
    ) -> str:
        text = self._remove_top_level_keys(
            text,
            {
                "model",
                "model_provider",
                "model_reasoning_effort",
                "model_context_window",
                "model_catalog_json",
            },
        )
        text = self._remove_table(text, provider_id).rstrip()
        escaped_model = json.dumps(model, ensure_ascii=False)
        escaped_url = json.dumps(base_url, ensure_ascii=False)
        escaped_catalog = json.dumps(str(catalog_path), ensure_ascii=False)
        escaped_provider_name = json.dumps(provider_name, ensure_ascii=False)
        reasoning_line = (
            f"model_reasoning_effort = {json.dumps(reasoning_effort)}\n"
            if reasoning_effort
            else ""
        )
        context_line = (
            f"model_context_window = {context_window}\n"
            if context_window > 0
            else ""
        )
        env_key_line = (
            f"env_key = {json.dumps(env_key)}\n"
            if env_key
            else ""
        )
        managed = (
            f'model = {escaped_model}\n'
            f"model_provider = {json.dumps(provider_id)}\n"
            f"{reasoning_line}"
            f"{context_line}\n"
            f"model_catalog_json = {escaped_catalog}\n\n"
            f"[model_providers.{provider_id}]\n"
            f"name = {escaped_provider_name}\n"
            f"base_url = {escaped_url}\n"
            f"{env_key_line}"
            'wire_api = "responses"\n'
        )
        return managed + ("\n" + text + "\n" if text else "")

    def _build_model_catalog(
        self,
        model: str,
        display_name: str,
        context_window: int,
        reasoning_options: tuple[str, ...] | None,
        reasoning_effort: str,
        input_modalities: tuple[str, ...],
        effective_context_window_percent: int,
        supports_parallel_tool_calls: bool,
        supports_reasoning_summaries: bool | None,
    ) -> dict[str, Any]:
        template = self._load_model_template()
        entry = dict(template)
        entry.update(
            {
                "slug": model,
                "display_name": display_name,
                "description": display_name,
                "priority": 1000,
                "additional_speed_tiers": [],
                "service_tiers": [],
                "availability_nux": None,
                "upgrade": None,
                "input_modalities": list(input_modalities),
                "supports_parallel_tool_calls": supports_parallel_tool_calls,
                "effective_context_window_percent": (
                    effective_context_window_percent
                ),
            }
        )
        if reasoning_options is not None:
            entry["supported_reasoning_levels"] = [
                {"effort": effort, "description": effort}
                for effort in reasoning_options
            ]
            entry["supports_reasoning_summaries"] = (
                bool(reasoning_options)
                if supports_reasoning_summaries is None
                else supports_reasoning_summaries
            )
            if reasoning_options:
                entry["default_reasoning_level"] = (
                    reasoning_effort
                    if reasoning_effort in reasoning_options
                    else reasoning_options[0]
                )
            else:
                entry.pop("default_reasoning_level", None)
        if context_window > 0:
            entry["context_window"] = context_window
            entry["max_context_window"] = context_window
        return {"models": [entry]}

    def _load_model_template(self) -> dict[str, Any]:
        cache_path = self.config_path.parent / "models_cache.json"
        if cache_path.exists():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                template = self._find_template(cached)
                if template:
                    return template
            except (OSError, json.JSONDecodeError):
                pass

        executable = shutil.which("codex")
        if executable:
            command = [executable, "debug", "models", "--bundled"]
            if os.name == "nt" and Path(executable).suffix.lower() in {".cmd", ".bat"}:
                command = ["cmd.exe", "/d", "/c", executable, "debug", "models", "--bundled"]
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if completed.returncode == 0:
                try:
                    template = self._find_template(json.loads(completed.stdout))
                    if template:
                        return template
                except json.JSONDecodeError:
                    pass
        raise RuntimeError(
            "无法读取 Codex 模型元数据模板，请确认 Codex CLI 已正确安装并重启本软件。"
        )

    @staticmethod
    def _find_template(catalog: Any) -> dict[str, Any] | None:
        if not isinstance(catalog, dict):
            return None
        models = catalog.get("models")
        if not isinstance(models, list):
            return None
        for entry in models:
            if isinstance(entry, dict) and entry.get("slug") == "gpt-5.5":
                return entry
        return next((entry for entry in models if isinstance(entry, dict)), None)
