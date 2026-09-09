"""
Unit and integration tests for Polkit security policy and NetworkHelperClient.
"""

from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
import pytest

from mislty.net.helper import (
    ValidationError,
    validate_interface,
    validate_dev_node,
    validate_ip,
    validate_metric,
)
from mislty.net.helper_client import NetworkHelperClient


def test_polkit_policy_xml_structure():
    """Verify XML validity and action metadata of org.mislty.policy."""
    policy_file = Path(__file__).resolve().parent.parent / "config" / "polkit" / "org.mislty.policy"
    assert policy_file.is_file()

    tree = ET.parse(policy_file)
    root = tree.getroot()
    assert root.tag == "policyconfig"

    vendor = root.find("vendor")
    assert vendor is not None
    assert "Purrfect Software Limited" in vendor.text

    action = root.find("action")
    assert action is not None
    assert action.get("id") == "org.mislty.network.control"

    defaults = action.find("defaults")
    assert defaults is not None
    allow_active = defaults.find("allow_active")
    assert allow_active is not None
    assert allow_active.text in ("auth_admin_keep", "yes")


def test_input_validation_interfaces():
    """Verify regex validation for network interface names."""
    for valid in ["ppp0", "wlan0", "wlan1", "eth0", "veth1"]:
        assert validate_interface(valid) == valid

    for invalid in ["; rm -rf /", "eth 0", "iface$foo", "a", "too_long_interface_name_here"]:
        with pytest.raises(ValidationError):
            validate_interface(invalid)


def test_input_validation_dev_nodes():
    """Verify regex validation for device node paths."""
    for valid in ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/mislty/data", "/dev/mislty/control"]:
        assert validate_dev_node(valid) == valid

    for invalid in ["/etc/passwd", "/dev/../etc/passwd", "ttyUSB0", "/dev/ttyUSB0; reboot"]:
        with pytest.raises(ValidationError):
            validate_dev_node(invalid)


def test_input_validation_ip_addresses():
    """Verify IPv4 address parsing and rejection of injection attempts."""
    for valid in ["192.168.100.1", "10.0.0.1", "8.8.8.8", "127.0.0.1"]:
        assert validate_ip(valid) == valid

    for invalid in ["256.0.0.1", "abc", "192.168.1.1; echo hi", ""]:
        with pytest.raises(ValidationError):
            validate_ip(invalid)


def test_input_validation_metrics():
    """Verify routing metric range and type validation."""
    assert validate_metric(50) == 50
    assert validate_metric("600") == 600
    assert validate_metric(0) == 0

    for invalid in [-1, 25000, "abc", None]:
        with pytest.raises(ValidationError):
            validate_metric(invalid)


def test_network_helper_client_auth():
    """Verify NetworkHelperClient executes check-auth via Polkit."""
    client = NetworkHelperClient()
    assert client.helper_path.exists()
    assert client.is_polkit_available is True
    assert client.check_auth() is True
