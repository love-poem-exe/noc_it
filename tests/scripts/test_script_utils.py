"""
Tests for the shared script utilities module.

Run with: python -m pytest tests/ -v
"""
import os
import json
import tempfile
import pytest

# Add project root to path so we can import the shared module
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.scripts.shared.script_utils import (
    is_ip_address,
    resolve_tunnel_target,
    load_json_file,
    save_json_file,
    read_full_output,
)


class TestIsIpAddress:
    def test_valid_ipv4(self):
        assert is_ip_address("192.168.1.1") is True
        assert is_ip_address("10.0.0.1") is True
        assert is_ip_address("255.255.255.255") is True
        assert is_ip_address("0.0.0.0") is True

    def test_invalid_values(self):
        assert is_ip_address("256.1.1.1") is False
        assert is_ip_address("hostname") is False
        assert is_ip_address("") is False
        assert is_ip_address(None) is False
        assert is_ip_address("192.168.1") is False
        assert is_ip_address("192.168.1.1.1") is False

    def test_hostname_with_dots(self):
        assert is_ip_address("pl-bol01a-br03") is False
        assert is_ip_address("device.example.com") is False


class TestResolveTunnelTarget:
    def test_prefers_dns_hostname(self):
        assert resolve_tunnel_target("device.example.com", "10.0.0.1") == "device.example.com"

    def test_falls_back_to_address_when_hostname_is_ip(self):
        assert resolve_tunnel_target("10.0.0.1", "172.16.0.1") == "172.16.0.1"

    def test_falls_back_to_hostname_ip_when_no_address(self):
        assert resolve_tunnel_target("10.0.0.1", None) == "10.0.0.1"
        assert resolve_tunnel_target("10.0.0.1", "") == "10.0.0.1"

    def test_returns_empty_when_nothing(self):
        assert resolve_tunnel_target(None, None) == ""
        assert resolve_tunnel_target("", "") == ""


class TestLoadSaveJson:
    def test_load_existing_file(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text(json.dumps([{"id": 1}]))
        result = load_json_file(str(p))
        assert result == [{"id": 1}]

    def test_load_nonexistent_file(self, tmp_path):
        result = load_json_file(str(tmp_path / "missing.json"), [])
        assert result == []

    def test_load_corrupt_json(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{invalid")
        result = load_json_file(str(p), {"default": True})
        assert result == {"default": True}

    def test_save_and_reload(self, tmp_path):
        p = tmp_path / "out.json"
        data = [{"name": "device1"}, {"name": "device2"}]
        save_json_file(str(p), data)
        loaded = load_json_file(str(p))
        assert loaded == data

    def test_save_unicode(self, tmp_path):
        p = tmp_path / "unicode.json"
        data = {"name": "urządzenie"}
        save_json_file(str(p), data)
        loaded = load_json_file(str(p))
        assert loaded["name"] == "urządzenie"
