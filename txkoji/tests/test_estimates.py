from datetime import timedelta
import pytest
import pytest_twisted
from txkoji import Connection
from txkoji.tests.util import FakeProxy
from txkoji.estimates import average_build_duration
from txkoji.estimates import average_build_durations


@pytest.fixture
def koji(monkeypatch):
    monkeypatch.setattr('txkoji.connection.Proxy', FakeProxy)
    koji = Connection('mykoji')
    return koji


@pytest_twisted.inlineCallbacks
def test_average_build_duration(koji):
    avg_duration = yield average_build_duration(koji, 'ceph-ansible')
    expected = timedelta(0, 143, 401978)
    assert avg_duration == expected


@pytest_twisted.inlineCallbacks
def test_average_build_durations(koji):
    avg_durations = yield average_build_durations(koji, ['ceph-ansible'])
    expected_delta = timedelta(0, 143, 401978)
    assert avg_durations == [expected_delta]
