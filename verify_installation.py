#!/usr/bin/env python3
"""Verify installation and basic functionality."""

import sys
from pathlib import Path


def check_imports() -> bool:
    """Check that all required packages can be imported."""
    print("Checking imports...")

    required = [
        "psutil",
        "rich",
        "sklearn",
        "matplotlib",
        "numpy",
        "pandas",
        "yaml",
        "typer",
        "joblib",
    ]

    failed = []
    for package in required:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError as e:
            print(f"  ✗ {package}: {e}")
            failed.append(package)

    if failed:
        print(f"\nFailed to import: {', '.join(failed)}")
        return False

    return True


def check_sysmon_imports() -> bool:
    """Check sysmon_ai package imports."""
    print("\nChecking sysmon_ai imports...")

    modules = [
        "sysmon_ai.config",
        "sysmon_ai.data",
        "sysmon_ai.ingest",
        "sysmon_ai.features",
        "sysmon_ai.models",
        "sysmon_ai.detection",
        "sysmon_ai.ui",
        "sysmon_ai.alerts",
        "sysmon_ai.evaluation",
        "sysmon_ai.cli",
    ]

    failed = []
    for module in modules:
        try:
            __import__(module)
            print(f"  ✓ {module}")
        except ImportError as e:
            print(f"  ✗ {module}: {e}")
            failed.append(module)

    if failed:
        print(f"\nFailed to import: {', '.join(failed)}")
        return False

    return True


def check_cli() -> bool:
    """Check CLI is accessible."""
    print("\nChecking CLI...")

    try:
        from sysmon_ai.cli import app

        print("  ✓ CLI app imported")
        return True
    except Exception as e:
        print(f"  ✗ Failed to import CLI: {e}")
        return False


def run_basic_test() -> bool:
    """Run a basic functionality test."""
    print("\nRunning basic functionality test...")

    try:
        import tempfile

        import numpy as np

        from sysmon_ai.data import Repository
        from sysmon_ai.features import FeatureTransformer
        from sysmon_ai.ingest import MetricsSampler
        from sysmon_ai.models import IsolationForestModel

        # Test sampler
        sampler = MetricsSampler("test-host")
        sample = sampler.sample()
        assert "cpu_pct" in sample
        print("  ✓ MetricsSampler works")

        # Test repository
        with tempfile.NamedTemporaryFile(suffix=".db") as f:
            repo = Repository(f.name)
            repo.connect()
            repo.initialize_schema()
            count = repo.write_samples([sample])
            assert count == 1
            repo.close()
        print("  ✓ Repository works")

        # Test model
        model = IsolationForestModel(n_estimators=10, random_state=42)
        X = np.random.randn(100, 5)
        model.fit(X)
        scores = model.score_samples(X)
        assert len(scores) == 100
        print("  ✓ IsolationForestModel works")

        return True

    except Exception as e:
        print(f"  ✗ Basic test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main() -> int:
    """Run all checks."""
    print("=" * 60)
    print("SysMon AI Installation Verification")
    print("=" * 60)

    checks = [
        ("Required packages", check_imports),
        ("SysMon AI modules", check_sysmon_imports),
        ("CLI", check_cli),
        ("Basic functionality", run_basic_test),
    ]

    results = []
    for name, check_func in checks:
        result = check_func()
        results.append((name, result))

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {name}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n✅ All checks passed! Installation is OK.")
        print("\nNext steps:")
        print("  1. Run 'sysmon init' to initialize")
        print("  2. Run 'sysmon start' to collect metrics")
        print("  3. Run 'sysmon dashboard' to view live dashboard")
        print("  4. See QUICKSTART.md for more details")
        return 0
    else:
        print("\n❌ Some checks failed. Please fix issues and try again.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
