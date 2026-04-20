"""CLI tests for tandemn-cli.

Ported from Tandemn-orca/tests/test_koi_integration.py after the CLI was
extracted to this repo. Tests cover:

- Koi integration helpers (KOI_SERVICE_URL, fetch_resources, _call_koi,
  _koi_summary_lines): behavior when Koi is unset / unreachable / slow.
- Subcommand help (ensures argparse wiring doesn't regress).

Not ported (no longer applicable after rebrand):
- test_cmd_deploy_uses_top_level_koi_predicted_tps_for_chunked_submit
  (the new cmd_deploy no longer references a `koi_predicted_tps` top-level
  payload field the same way; behavior is covered by the per-replica
  webhook tests in Orca's server-side test suite).
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = REPO_ROOT / "tandemn.py"


def _load_tandemn_module():
    """Load tandemn.py as an importable module for white-box tests."""
    spec = importlib.util.spec_from_file_location("tandemn_cli", CLI_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def tandemn_mod():
    return _load_tandemn_module()


# ──────────────────────────────────────────────────────────────────────────────
# Koi helpers — fail-closed behavior
# ──────────────────────────────────────────────────────────────────────────────


class TestKoiHelpers:
    def test_koi_service_url_attribute_exists(self, tandemn_mod):
        """CLI exposes KOI_SERVICE_URL as a module-level config."""
        assert hasattr(tandemn_mod, "KOI_SERVICE_URL")
        assert isinstance(tandemn_mod.KOI_SERVICE_URL, str)

    def test_fetch_resources_returns_none_on_failure(self, tandemn_mod):
        """fetch_resources returns None when server is unreachable."""
        original = tandemn_mod.TD_SERVER
        tandemn_mod.TD_SERVER = "http://127.0.0.1:1"
        try:
            assert tandemn_mod.fetch_resources() is None
        finally:
            tandemn_mod.TD_SERVER = original

    def test_call_koi_returns_none_when_disabled(self, tandemn_mod):
        """_call_koi returns None when KOI_SERVICE_URL is empty."""
        original = tandemn_mod.KOI_SERVICE_URL
        tandemn_mod.KOI_SERVICE_URL = ""
        try:
            result = tandemn_mod._call_koi(
                {"model_name": "test"}, {"resources": []}
            )
            assert result is None
        finally:
            tandemn_mod.KOI_SERVICE_URL = original

    def test_call_koi_returns_none_on_connection_error(self, tandemn_mod):
        """_call_koi returns None when Koi service is unreachable."""
        original = tandemn_mod.KOI_SERVICE_URL
        tandemn_mod.KOI_SERVICE_URL = "http://127.0.0.1:1"
        try:
            result = tandemn_mod._call_koi(
                {"model_name": "test"}, {"resources": []}, timeout=1
            )
            assert result is None
        finally:
            tandemn_mod.KOI_SERVICE_URL = original

    def test_call_koi_returns_none_on_malformed_json(self, tandemn_mod):
        """_call_koi fails closed if Koi returns invalid JSON."""
        original = tandemn_mod.KOI_SERVICE_URL
        tandemn_mod.KOI_SERVICE_URL = "http://koi:8090"
        bad_response = MagicMock(status_code=200)
        bad_response.json.side_effect = ValueError("invalid json")
        try:
            with patch.object(tandemn_mod.requests, "post", return_value=bad_response):
                result = tandemn_mod._call_koi(
                    {"model_name": "test"}, {"resources": []}, timeout=1
                )
            assert result is None
        finally:
            tandemn_mod.KOI_SERVICE_URL = original

    def test_call_koi_returns_none_on_timeout(self, tandemn_mod):
        """_call_koi fails closed if Koi times out."""
        original = tandemn_mod.KOI_SERVICE_URL
        tandemn_mod.KOI_SERVICE_URL = "http://koi:8090"
        try:
            with patch.object(
                tandemn_mod.requests,
                "post",
                side_effect=tandemn_mod.requests.Timeout,
            ):
                result = tandemn_mod._call_koi(
                    {"model_name": "test"}, {"resources": []}, timeout=1
                )
            assert result is None
        finally:
            tandemn_mod.KOI_SERVICE_URL = original

    def test_koi_summary_lines_basic(self, tandemn_mod):
        """_koi_summary_lines produces display lines from a full Koi response."""
        koi_data = {
            "config": {
                "gpu_type": "L40S",
                "instance_type": "g6e.12xlarge",
                "tp": 4,
                "pp": 1,
                "dp": 2,
                "num_instances": 2,
                "engine_config": {"max_model_len": 8192, "max_num_seqs": 64},
            },
            "predicted_tps": 2500.0,
            "predicted_cost_per_hour": 9.36,
            "predicted_runtime_hours": 3.2,
            "predicted_total_cost": 29.95,
            "confidence": 0.78,
        }
        lines = tandemn_mod._koi_summary_lines(koi_data)
        assert len(lines) > 0
        text = "\n".join(lines)
        assert "L40S" in text
        assert "g6e.12xlarge" in text
        assert "2500" in text
        assert "9.36" in text

    def test_koi_summary_lines_minimal(self, tandemn_mod):
        """_koi_summary_lines handles a minimal Koi response."""
        koi_data = {
            "config": {
                "gpu_type": "A100",
                "instance_type": "p4d.24xlarge",
                "tp": 8,
                "pp": 1,
                "dp": 1,
                "num_instances": 1,
                "engine_config": {},
            },
        }
        lines = tandemn_mod._koi_summary_lines(koi_data)
        assert len(lines) >= 3  # instance, GPU, parallelism lines at minimum


# ──────────────────────────────────────────────────────────────────────────────
# Subcommand help — argparse wiring regression guard
# ──────────────────────────────────────────────────────────────────────────────


class TestSubcommandHelp:
    def _cli(self, *args, timeout=10):
        return subprocess.run(
            [sys.executable, str(CLI_PATH), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def test_top_level_help(self):
        r = self._cli("--help")
        assert r.returncode == 0
        for sub in ("deploy", "plan", "progress", "status", "logs", "clusters", "destroy"):
            assert sub in r.stdout, f"subcommand {sub!r} missing from top-level help"

    def test_plan_help_works(self):
        r = self._cli("plan", "--help")
        assert r.returncode == 0
        assert "model_name" in r.stdout

    def test_deploy_help_works(self):
        r = self._cli("deploy", "--help")
        assert r.returncode == 0
        assert "--slo" in r.stdout
        assert "--skip-dangerously" in r.stdout

    def test_deploy_has_no_advisor_flag(self):
        r = self._cli("deploy", "--help")
        assert "--no-advisor" in r.stdout

    def test_logs_help_works(self):
        r = self._cli("logs", "--help")
        assert r.returncode == 0

    def test_clusters_help_works(self):
        r = self._cli("clusters", "--help")
        assert r.returncode == 0

    def test_destroy_help_works(self):
        r = self._cli("destroy", "--help")
        assert r.returncode == 0
        assert "--all" in r.stdout
