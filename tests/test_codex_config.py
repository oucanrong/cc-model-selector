from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.core.config_manager import ConfigManager, ProxyConfig, ProxyItem
from src.core.constants import (
    CODEX_API_KEY_ENV,
    CODEX_PROVIDER_DEFAULTS,
    CODEX_PROVIDER_OPTIONS,
    PROVIDER_OPTIONS,
)
from src.services.codex_config_service import CodexConfigService


class CodexConfigTests(unittest.TestCase):
    @staticmethod
    def _template() -> dict:
        return {
            "slug": "gpt-5.5",
            "display_name": "GPT-5.5",
            "description": "Template",
            "base_instructions": "You are Codex.",
            "model_messages": {"instructions_template": "test"},
            "supported_reasoning_levels": [{"effort": "high"}],
            "context_window": 272000,
            "max_context_window": 272000,
        }

    def test_legacy_config_is_upgraded_with_codex_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "provider": "Claude官方接口",
                        "provider_settings": {},
                        "auth_tokens": {},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            manager = ConfigManager(path)
            config = manager.load()
            self.assertEqual(config.codex.provider, "Codex官方接口")
            self.assertEqual(
                config.codex.provider_settings["DeepSeek"].model,
                "deepseek-v4-pro",
            )
            manager.save(config)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("codex", saved)
            self.assertEqual(
                saved["codex"]["provider_settings"]["Kimi"]["model"],
                "kimi-k2.6",
            )
            self.assertEqual(
                set(saved["codex"]["provider_settings"]),
                set(CODEX_PROVIDER_OPTIONS),
            )

    def test_provider_defaults_and_legacy_minimax_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "provider": "MINIMAX",
                        "auth_tokens": {"MINIMAX": "legacy-key"},
                        "provider_settings": {
                            "MINIMAX": {
                                "base_url": "https://legacy.example",
                                "token": "legacy-key",
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            config = ConfigManager(path).load()
            self.assertEqual(config.provider, "MiniMax")
            self.assertEqual(config.auth_tokens["MiniMax"], "legacy-key")
            self.assertEqual(
                config.provider_settings["MiniMax"].base_url,
                "https://legacy.example",
            )
            self.assertEqual(
                config.codex.provider_settings["阿里千问"].model,
                "qwen3.7-max",
            )
            self.assertEqual(
                config.codex.provider_settings["GPT中转"].reasoning_effort,
                "medium",
            )
            self.assertEqual(
                CODEX_PROVIDER_DEFAULTS["Kimi"]["context_window"],
                256_000,
            )
            self.assertEqual(
                CODEX_PROVIDER_DEFAULTS["智谱GLM"]["reasoning_options"],
                (),
            )
            self.assertEqual(
                config.codex.provider_settings["智谱GLM"].reasoning_effort,
                "",
            )
            self.assertTrue(
                config.codex.provider_settings["Kimi"].thinking_enabled,
            )
            self.assertTrue(
                config.codex.provider_settings["智谱GLM"].thinking_enabled,
            )
            self.assertTrue(
                config.codex.provider_settings["小米MiMo"].thinking_enabled,
            )
            self.assertFalse(
                config.codex.provider_settings["MiniMax"].thinking_enabled,
            )

    def test_direct_provider_matrix(self) -> None:
        qwen = CODEX_PROVIDER_DEFAULTS["阿里千问"]
        self.assertEqual(
            qwen["models"],
            ("qwen3.6-flash", "qwen3.7-plus", "qwen3.7-max"),
        )
        self.assertEqual(qwen["default_model"], "qwen3.7-max")
        self.assertEqual(qwen["protocol"], "responses_direct")
        self.assertEqual(qwen["context_windows"]["qwen3.6-flash"], 256_000)
        self.assertEqual(qwen["context_windows"]["qwen3.7-max"], 1_000_000)

        minimax = CODEX_PROVIDER_DEFAULTS["MiniMax"]
        self.assertEqual(minimax["models"], ("MiniMax-M3",))
        self.assertEqual(minimax["context_window"], 512_000)
        self.assertEqual(minimax["reasoning_options"], ())
        self.assertEqual(minimax["protocol"], "responses_direct")

        relay = CODEX_PROVIDER_DEFAULTS["GPT中转"]
        self.assertEqual(relay["models"], ("gpt-5.5",))
        self.assertEqual(relay["default_reasoning_effort"], "medium")
        self.assertEqual(relay["protocol"], "responses_direct")

        deepseek = CODEX_PROVIDER_DEFAULTS["DeepSeek"]
        self.assertEqual(
            deepseek["reasoning_options"],
            ("none", "high", "max"),
        )
        self.assertEqual(
            deepseek["chat_reasoning"]["effort_map"],
            {"low": "high", "medium": "high", "xhigh": "max"},
        )

    def test_legacy_deepseek_reasoning_effort_is_mapped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "codex": {
                            "provider": "DeepSeek",
                            "provider_settings": {
                                "DeepSeek": {
                                    "reasoning_effort": "xhigh",
                                }
                            },
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            config = ConfigManager(path).load()
            self.assertEqual(
                config.codex.provider_settings["DeepSeek"].reasoning_effort,
                "max",
            )

    def test_legacy_codex_ark_name_is_migrated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "codex": {
                            "provider": "方舟 Coding Plan",
                            "provider_settings": {
                                "方舟 Coding Plan": {
                                    "base_url": "https://ark.example/v3",
                                    "token": "ark-key",
                                    "model": "doubao-seed-2.0-code",
                                }
                            },
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            config = ConfigManager(path).load()
            self.assertEqual(config.codex.provider, "方舟Coding Plan")
            self.assertEqual(
                config.codex.provider_settings["方舟Coding Plan"].token,
                "ark-key",
            )

    def test_each_provider_target_proxy_is_saved_and_reloaded_independently(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text("{}", encoding="utf-8")
            manager = ConfigManager(path)
            config = manager.load()

            claude_proxies = {}
            for provider_index, provider in enumerate(PROVIDER_OPTIONS, start=1):
                for target_index, target in enumerate(("cli", "upgrade"), start=1):
                    proxy = self._proxy_for_index(provider_index * 10 + target_index)
                    config.provider_settings[provider].proxies[target] = proxy
                    claude_proxies[(provider, target)] = proxy
            codex_proxies = {}
            for provider_index, provider in enumerate(
                CODEX_PROVIDER_OPTIONS,
                start=1,
            ):
                for target_index, target in enumerate(("cli", "upgrade"), start=1):
                    proxy = self._proxy_for_index(
                        100 + provider_index * 10 + target_index
                    )
                    config.codex.provider_settings[provider].proxies[target] = proxy
                    codex_proxies[(provider, target)] = proxy
            config.provider = PROVIDER_OPTIONS[0]
            config.claude_launch_target = "cli"
            config.proxy = claude_proxies[(config.provider, "cli")]
            config.codex.launch_target = "cli"
            config.codex.provider_settings[
                config.codex.provider
            ].proxy = codex_proxies[(config.codex.provider, "cli")]
            manager.save(config)

            loaded = manager.load()

            for (provider, target), proxy in claude_proxies.items():
                self.assertEqual(
                    loaded.provider_settings[provider].proxies[target],
                    proxy,
                )
            for (provider, target), proxy in codex_proxies.items():
                self.assertEqual(
                    loaded.codex.provider_settings[provider].proxies[target],
                    proxy,
                )
            for provider in PROVIDER_OPTIONS:
                self.assertEqual(
                    loaded.provider_settings[provider].proxies["vscode"],
                    ProxyConfig(),
                )
            for provider in CODEX_PROVIDER_OPTIONS:
                self.assertEqual(
                    loaded.codex.provider_settings[provider].proxies["desktop"],
                    ProxyConfig(),
                )
                self.assertEqual(
                    loaded.codex.provider_settings[provider].proxies["vscode"],
                    ProxyConfig(),
                )

            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn(
                "proxy",
                saved["provider_settings"][PROVIDER_OPTIONS[0]],
            )
            self.assertNotIn(
                "proxy",
                saved["codex"]["provider_settings"][CODEX_PROVIDER_OPTIONS[0]],
            )

    @staticmethod
    def _proxy_for_index(index: int) -> ProxyConfig:
        return ProxyConfig(
            http=ProxyItem(
                enabled=index % 2 == 0,
                host=f"10.{index}.0.1",
                port=str(8000 + index),
                auth=f"http-{index}",
            ),
            https=ProxyItem(
                enabled=True,
                host=f"10.{index}.0.2",
                port=str(9000 + index),
                auth=f"https-{index}",
            ),
            socks5=ProxyItem(
                enabled=index % 3 == 0,
                host=f"10.{index}.0.3",
                port=str(10000 + index),
                auth=f"socks-{index}",
            ),
        )

    def test_codex_toml_is_restored_byte_for_byte(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "config.toml"
            state_path = root / "restore.json"
            original = (
                'model = "original-model"\r\n'
                'model_provider = "original-provider"\r\n'
                '\r\n[mcp_servers.demo]\r\ncommand = "demo"\r\n'
            ).encode("utf-8")
            config_path.write_bytes(original)
            service = CodexConfigService(config_path, state_path)
            with patch.object(
                service,
                "_load_model_template",
                return_value=self._template(),
            ):
                service.activate(
                    "deepseek-v4-pro",
                    "http://127.0.0.1:32100/v1",
                    "DeepSeek V4 Pro",
                    1_000_000,
                )
            active = config_path.read_text(encoding="utf-8")
            self.assertIn('model_provider = "cc_model_manager"', active)
            self.assertIn("model_catalog_json", active)
            self.assertIn("[mcp_servers.demo]", active)
            catalog = json.loads(service.catalog_path.read_text(encoding="utf-8"))
            self.assertEqual(catalog["models"][0]["slug"], "deepseek-v4-pro")
            self.assertEqual(
                catalog["models"][0]["context_window"],
                1_000_000,
            )
            self.assertEqual(
                catalog["models"][0]["display_name"],
                "DeepSeek V4 Pro",
            )
            service.restore()
            self.assertEqual(config_path.read_bytes(), original)
            self.assertFalse(state_path.exists())
            self.assertFalse(service.catalog_path.exists())

    def test_crash_recovery_uses_persisted_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "config.toml"
            state_path = root / "restore.json"
            config_path.write_text('approval_policy = "on-request"\n', encoding="utf-8")
            first = CodexConfigService(config_path, state_path)
            with patch.object(
                first,
                "_load_model_template",
                return_value=self._template(),
            ):
                first.activate("glm-5.1", "http://127.0.0.1:12345/v1")
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["owner_pid"] = 99999999
            state_path.write_text(json.dumps(state), encoding="utf-8")
            recovered = CodexConfigService(config_path, state_path)
            self.assertTrue(recovered.recover_if_needed())
            self.assertEqual(
                config_path.read_text(encoding="utf-8"),
                'approval_policy = "on-request"\n',
            )

    def test_live_owner_is_not_treated_as_crash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "config.toml"
            state_path = root / "restore.json"
            config_path.write_text('model = "original"\n', encoding="utf-8")
            active = CodexConfigService(config_path, state_path)
            with patch.object(
                active,
                "_load_model_template",
                return_value=self._template(),
            ):
                active.activate("kimi-k2.6", "http://127.0.0.1:12345/v1")
            second_instance = CodexConfigService(config_path, state_path)
            self.assertFalse(second_instance.recover_if_needed())
            self.assertIn(
                'model = "kimi-k2.6"',
                config_path.read_text(encoding="utf-8"),
            )
            active.restore()

    def test_direct_responses_config_uses_env_key_without_real_token(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "config.toml"
            state_path = root / "restore.json"
            config_path.write_text(
                'approval_policy = "on-request"\n',
                encoding="utf-8",
            )
            service = CodexConfigService(config_path, state_path)
            with patch.object(
                service,
                "_load_model_template",
                return_value=self._template(),
            ):
                service.activate(
                    model="qwen3.7-max",
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                    display_name="Qwen 3.7 Max",
                    context_window=1_000_000,
                    provider_id="qwen",
                    provider_name="阿里千问",
                    reasoning_effort="medium",
                    env_key=CODEX_API_KEY_ENV,
                )
            active = config_path.read_text(encoding="utf-8")
            self.assertIn('model_provider = "qwen"', active)
            self.assertIn('model_reasoning_effort = "medium"', active)
            self.assertIn("model_context_window = 1000000", active)
            self.assertIn("[model_providers.qwen]", active)
            self.assertIn(f'env_key = "{CODEX_API_KEY_ENV}"', active)
            self.assertNotIn("real-api-key", active)
            self.assertIn('approval_policy = "on-request"', active)
            service.restore()


if __name__ == "__main__":
    unittest.main()
