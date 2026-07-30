def test_package_importable():
    import importlib.metadata

    assert importlib.metadata.version("testscope-mcp") == "0.1.0"
