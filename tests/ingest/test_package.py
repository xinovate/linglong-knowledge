"""Tests for SourcePackage YAML loading."""

import tempfile
from pathlib import Path

from linglong.ingest.package import (
    DimensionConfig,
    FilterConfig,
    OutputConfig,
    SearchConfig,
    SourcePackage,
    VerificationSettings,
)


def test_load_package_inline():
    """Load a package from inline config (as in .linglong.yaml ingest.packages)."""
    package = SourcePackage(
        name="test-inline",
        topic="AI 测试",
        sources=[
            {"id": "aihot", "type": "aihot", "config": {"endpoint": "daily"}},
        ],
        dimensions=[
            DimensionConfig(
                name="公司决策",
                search=SearchConfig(keywords=["OpenAI"]),
                filter=FilterConfig(max_results=5),
            ),
        ],
    )
    assert package.name == "test-inline"
    assert len(package.sources) == 1
    assert package.sources[0].type == "aihot"
    assert len(package.dimensions) == 1


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


def test_dimension_config_from_yaml():
    """Load a package with dimensions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = Path(tmpdir) / "dim-test.yaml"
        pkg_file.write_text("""
name: "Dimension Test"
topic: "AI"
dimensions:
  - name: "研究员观点"
    search:
      keywords:
        - "Karpathy AI"
        - "LeCun world model"
      engine: bing_cn
    filter:
      max_results: 3
      max_age_days: 7
  - name: "公司决策"
    search:
      keywords:
        - "OpenAI"
    filter:
      max_results: 5
output:
  format: morning-brief
  persist: true
""")
        pkg = SourcePackage.from_yaml(pkg_file)
        assert len(pkg.dimensions) == 2
        assert pkg.dimensions[0].name == "研究员观点"
        assert pkg.dimensions[0].search.keywords == ["Karpathy AI", "LeCun world model"]
        assert pkg.dimensions[0].filter.max_results == 3
        assert pkg.dimensions[1].filter.max_results == 5
        assert pkg.output.format == "morning-brief"
        assert pkg.output.persist is True


def test_backward_compatible_no_dimensions():
    """Package without dimensions still works."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg_file = Path(tmpdir) / "legacy.yaml"
        pkg_file.write_text("""
name: "Legacy"
topic: "test"
sources:
  - id: "s1"
    type: rss
    config:
      url: "https://example.com/rss"
""")
        pkg = SourcePackage.from_yaml(pkg_file)
        assert pkg.dimensions == []
        assert pkg.output.format == ""
