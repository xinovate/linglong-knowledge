"""Tests for SourcePackage YAML loading."""

import tempfile
from pathlib import Path

from linglong.ingest.package import SourcePackage, VerificationSettings


def test_load_ai_morning_brief_package():
    """Load the example AI morning brief package."""
    package = SourcePackage.from_yaml("docs/examples/packages/ai-morning-brief.yaml")
    assert package.name == "AI Morning Brief"
    assert package.topic == "artificial-intelligence"
    assert len(package.sources) == 4
    assert package.sources[0].type == "rss"
    assert package.sources[2].type == "web_fetch"
    assert package.verification.cross_reference_min == 2


def test_package_load_all_from_directory():
    """Load all packages from a directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = Path(tmpdir) / "test.yaml"
        pkg_file.write_text("""
name: "Test Package"
topic: "test"
sources:
  - id: "test-source"
    type: rss
    config:
      url: "https://example.com/rss"
""")
        packages = SourcePackage.load_all([tmpdir])
        assert len(packages) == 1
        assert packages[0].name == "Test Package"


def test_verification_settings_defaults():
    """VerificationSettings has sensible defaults."""
    v = VerificationSettings()
    assert v.enabled is True
    assert v.cross_reference_min == 1
    assert v.max_age_days == 7
