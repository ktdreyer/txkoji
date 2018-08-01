import os
import pytest


# pytest_plugins = "pytest_twisted"


TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(TESTS_DIR, 'fixtures')


@pytest.fixture(autouse=True)
def profile_location(monkeypatch):
    monkeypatch.setattr('txkoji.connection.PROFILES', FIXTURES_DIR + '/*.conf')
