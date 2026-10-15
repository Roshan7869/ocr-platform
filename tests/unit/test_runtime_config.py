"""Fail-closed unit tests for the runtime.yaml loader."""

import copy
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from ocr_platform.runtime_config import (
    DEFAULT_RUNTIME_CONFIG_PATH,
    RuntimeConfigError,
    configuration_fingerprint,
    load_runtime_config,
)


def _read_settings() -> dict:
    return yaml.safe_load(DEFAULT_RUNTIME_CONFIG_PATH.read_text(encoding="utf-8"))


class RuntimeConfigTests(unittest.TestCase):
    def test_required_keys_present_loads(self):
        cfg = load_runtime_config()
        self.assertEqual(cfg.render["dpi"], 200)
        self.assertEqual(cfg.coordinates["coordinate_system"], "image_top_left_normalized")
        self.assertEqual(len(cfg.fingerprint), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in cfg.fingerprint))

    def test_unknown_top_level_key_rejected(self):
        settings = _read_settings()
        settings["sneaky_section"] = {}
        with self.assertRaises(RuntimeConfigError):
            load_runtime_config(self._write_tmp(settings))

    def test_unknown_nested_key_rejected(self):
        settings = _read_settings()
        settings["render"]["sneaky_key"] = 1
        with self.assertRaises(RuntimeConfigError):
            load_runtime_config(self._write_tmp(settings))

    def test_missing_key_fails_closed(self):
        for section, key in [
            ("render", "dpi"),
            ("coordinates", "coordinate_system"),
            ("preprocess", "deskew"),
            ("comparison_policy", "cpu_render_pixel_tolerance"),
        ]:
            with self.subTest(section=section, key=key):
                settings = _read_settings()
                del settings[section][key]
                with self.assertRaises(RuntimeConfigError):
                    load_runtime_config(self._write_tmp(settings))

    def test_missing_section_fails_closed(self):
        settings = _read_settings()
        del settings["preprocess"]
        with self.assertRaises(RuntimeConfigError):
            load_runtime_config(self._write_tmp(settings))

    def test_fingerprint_changes_when_dpi_changes(self):
        base = load_runtime_config().as_dict()
        mutated = copy.deepcopy(base)
        mutated["render"]["dpi"] = 300
        self.assertNotEqual(configuration_fingerprint(base), configuration_fingerprint(mutated))

    def test_cpu_render_pixel_tolerance_is_zero(self):
        cfg = load_runtime_config()
        self.assertEqual(cfg.comparison_policy["cpu_render_pixel_tolerance"], 0)

    def test_nonzero_cpu_tolerance_rejected(self):
        settings = _read_settings()
        settings["comparison_policy"]["cpu_render_pixel_tolerance"] = 1
        with self.assertRaises(RuntimeConfigError):
            load_runtime_config(self._write_tmp(settings))

    def _write_tmp(self, settings: dict) -> Path:
        tmp = Path(self._tmp_dir()) / "runtime.yaml"
        tmp.write_text(yaml.safe_dump(settings), encoding="utf-8")
        return tmp

    def _tmp_dir(self) -> str:
        holder = tempfile.mkdtemp(prefix="runtime-config-test-")
        self.addCleanup(shutil.rmtree, holder, True)
        return holder


if __name__ == "__main__":
    unittest.main()
