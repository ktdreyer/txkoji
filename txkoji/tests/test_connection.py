import pytest
from txkoji import Connection


def test_basic():
    koji = Connection('mykoji')
    assert koji
    assert koji.url == 'https://hub.example.com/kojihub'


def test_missing_profile(monkeypatch):
    monkeypatch.setattr('txkoji.PROFILES', '/noexist')
    with pytest.raises(ValueError):
        Connection('mykoji')
