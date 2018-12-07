from datetime import timedelta
import pytest
from txkoji import Connection
from txkoji.tests.util import FakeProxy
from txkoji.estimates import average_build_duration


@pytest.fixture
def koji(monkeypatch):
    monkeypatch.setattr('txkoji.connection.Proxy', FakeProxy)
    koji = Connection('mykoji')
    return koji


@pytest.inlineCallbacks
def test_average_build_duration(koji):
    avg_duration = yield average_build_duration(koji, 'ceph-ansible')
    expected = timedelta(0, 143, 401978)
    assert avg_duration == expected
