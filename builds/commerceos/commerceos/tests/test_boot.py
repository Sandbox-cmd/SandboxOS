"""A1's check: the repo boots — the package imports and the app constructs."""

def test_package_imports():
    import commerceos
    assert commerceos.__version__

def test_all_parts_import():
    import commerceos.spine, commerceos.gate, commerceos.watching  # noqa: F401
    import commerceos.fleet, commerceos.catalog, commerceos.economics  # noqa: F401
    import commerceos.web  # noqa: F401
