from datetime import timedelta
from twisted.internet import defer
import pytest
import pytest_twisted
from txkoji import Connection
from txkoji.proxy import TrustedProxy
from txkoji.tests.util import FakeProxy
from txkoji.estimates import average_build_duration
from txkoji.estimates import average_build_durations


@pytest.fixture
def koji(monkeypatch):
    monkeypatch.setattr('txkoji.connection.TrustedProxy', FakeProxy)
    koji = Connection('mykoji')
    return koji


class FakeMulticallProxy(TrustedProxy):

    def callRemote(self, action, *args):
        """
        Return a deferred that always fires successfully for system.multicall

        This expects every multicall to be "getAverageBuildDuration" and
        returns a hard-coded float value for that.
        """
        if action != 'system.multicall':
            raise ValueError(action)
        calls = args[0]
        response = []
        for call in calls:
            assert call['methodName'] == 'getAverageBuildDuration'
            result = 143.401978
            response.append([result])
        return defer.succeed(response)


@pytest_twisted.inlineCallbacks
def test_average_build_duration(koji):
    avg_duration = yield average_build_duration(koji, 'ceph-ansible')
    expected = timedelta(0, 143, 401978)
    assert avg_duration == expected


@pytest_twisted.inlineCallbacks
def test_average_build_durations(monkeypatch):
    monkeypatch.setattr('txkoji.connection.TrustedProxy', FakeMulticallProxy)
    koji = Connection('mykoji')
    avg_durations = yield average_build_durations(koji, ['ceph-ansible'])
    expected_delta = timedelta(0, 143, 401978)
    assert list(avg_durations) == [expected_delta]
