"""Integration tests conftest — ensure all tests share one event loop."""

def pytest_configure(config):
    config.option.asyncio_mode = "auto"
    config.option.asyncio_default_test_loop_scope = "session"
