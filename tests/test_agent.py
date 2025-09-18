def test_version():
    """Test that version is accessible."""
    from playwright_analyzer import __version__

    assert __version__ == "0.1.2"
