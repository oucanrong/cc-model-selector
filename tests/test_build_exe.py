from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_exe
from src.core.constants import application_root


class BuildExeTests(unittest.TestCase):
    def test_install_packages_prefers_uv_for_environment_without_pip(self) -> None:
        with (
            patch("build_exe.shutil.which", return_value=r"C:\bin\uv.exe"),
            patch("build_exe.subprocess.run") as run,
        ):
            build_exe.install_packages(["PyInstaller"])

        run.assert_called_once_with(
            [
                r"C:\bin\uv.exe",
                "pip",
                "install",
                "--python",
                build_exe.sys.executable,
                "PyInstaller",
            ],
            check=True,
        )

    def test_ensure_dependencies_skips_install_when_complete(self) -> None:
        with (
            patch("build_exe.missing_packages", return_value=[]),
            patch("build_exe.install_packages") as install,
        ):
            build_exe.ensure_dependencies(["Pillow", "PyInstaller"])

        install.assert_not_called()

    def test_install_packages_reports_missing_installer(self) -> None:
        with (
            patch("build_exe.shutil.which", return_value=None),
            patch("build_exe.importlib.util.find_spec", return_value=None),
        ):
            with self.assertRaisesRegex(RuntimeError, "缺少 pip"):
                build_exe.install_packages(["PyInstaller"])

    def test_frozen_application_root_uses_executable_directory(self) -> None:
        executable = Path(r"C:\Apps\cc模型管理器\cc模型管理器.exe")
        with (
            patch("src.core.constants.sys.frozen", True, create=True),
            patch("src.core.constants.sys.executable", str(executable)),
        ):
            self.assertEqual(application_root(), executable.parent)

    def test_copy_distribution_files_places_example_next_to_exe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist_dir = root / "dist" / build_exe.PROJECT_NAME
            dist_dir.mkdir(parents=True)
            source = root / build_exe.EXAMPLE_CONFIG
            source.write_text('{"provider": "Claude官方接口"}\n', encoding="utf-8")

            build_exe.copy_distribution_files(root, dist_dir)

            target = dist_dir / build_exe.EXAMPLE_CONFIG
            self.assertEqual(target.read_text(encoding="utf-8"), source.read_text(encoding="utf-8"))

    def test_copy_distribution_files_requires_example_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist_dir = root / "dist" / build_exe.PROJECT_NAME
            dist_dir.mkdir(parents=True)

            with self.assertRaises(FileNotFoundError):
                build_exe.copy_distribution_files(root, dist_dir)


if __name__ == "__main__":
    unittest.main()
