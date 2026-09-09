"""
Unit tests for deployment scripts and zero-internet offline installer:
- Shell syntax validation (bash -n)
- Script file permissions
- Systemd user service unit syntax validation
- Offline bundle generator and manifest checks
"""

import os
from pathlib import Path
import subprocess
import pytest


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def test_deploy_scripts_syntax(repo_root):
    """Verify that all deployment shell scripts pass bash -n syntax checks."""
    scripts = [
        repo_root / "deploy" / "install.sh",
        repo_root / "deploy" / "uninstall.sh",
        repo_root / "deploy" / "build_offline_bundle.sh",
        repo_root / "bin" / "mislty-net-helper",
    ]
    for script in scripts:
        assert script.is_file(), f"Script {script} does not exist."
        res = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
        assert res.returncode == 0, f"Syntax error in {script}: {res.stderr}"


def test_deploy_scripts_executable(repo_root):
    """Verify that deployment scripts are marked executable."""
    scripts = [
        repo_root / "deploy" / "install.sh",
        repo_root / "deploy" / "uninstall.sh",
        repo_root / "deploy" / "build_offline_bundle.sh",
    ]
    for script in scripts:
        assert os.access(script, os.X_OK), f"{script} is not executable."


def test_systemd_service_syntax(repo_root):
    """Verify syntax of config/systemd/misltyd.service."""
    unit_file = repo_root / "config" / "systemd" / "misltyd.service"
    assert unit_file.is_file()

    content = unit_file.read_text(encoding="utf-8")
    assert "[Unit]" in content
    assert "[Service]" in content
    assert "[Install]" in content
    assert "ExecStart=/usr/local/bin/misltyd --foreground" in content
    assert "WantedBy=default.target" in content


def test_offline_bundle_generation(repo_root, tmp_path):
    """Verify build_offline_bundle.sh execution and bundle contents."""
    target_dir = tmp_path / "test-bundle"
    builder = repo_root / "deploy" / "build_offline_bundle.sh"

    res = subprocess.run([str(builder), str(target_dir)], capture_output=True, text=True)
    assert res.returncode == 0, f"Builder failed: {res.stderr}"

    # Verify essential bundle artifacts
    assert (target_dir / "INSTALL.sh").is_file()
    assert os.access(target_dir / "INSTALL.sh", os.X_OK)

    assert (target_dir / "deploy" / "install.sh").is_file()
    assert (target_dir / "deploy" / "uninstall.sh").is_file()

    assert (target_dir / "config" / "udev" / "99-ufi-permissions.rules").is_file()
    assert (target_dir / "config" / "polkit" / "org.mislty.policy").is_file()
    assert (target_dir / "config" / "polkit" / "49-mislty.rules").is_file()
    assert (target_dir / "config" / "systemd" / "misltyd.service").is_file()

    assert (target_dir / "src" / "mislty" / "core" / "daemon.py").is_file()
    assert (target_dir / "src" / "mislty" / "cli" / "main.py").is_file()
    assert (target_dir / "src" / "mislty" / "ipc" / "client.py").is_file()
    assert (target_dir / "bin" / "mislty-net-helper").is_file()
