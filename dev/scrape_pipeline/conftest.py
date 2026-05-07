"""pytest configuration for dev/scrape_pipeline/ — registers the 'network' marker."""
import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "network: mark test as requiring real network access (pass --network to run)")


def pytest_addoption(parser):
    parser.addoption("--network", action="store_true", default=False, help="run tests that make real network requests")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--network"):
        skip_network = pytest.mark.skip(reason="network test — pass --network to run")
        for item in items:
            if "network" in item.keywords:
                item.add_marker(skip_network)
