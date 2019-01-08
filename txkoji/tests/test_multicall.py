from twisted.web.xmlrpc import Proxy
from twisted.internet import defer
import pytest
import pytest_twisted
from txkoji import Connection
from txkoji.exceptions import KojiException
from txkoji.task import Task


class FakeProxy(Proxy):

    # Some hard-coded results for some methods:
    results = {
        'getAPIVersion': 1,
        'getTaskInfo': {'id': 12345, 'method': 'tagBuild'},
    }

    def callRemote(self, action, *args):
        """
        Return a deferred that always fires successfully for system.multicall
        """
        if action != 'system.multicall':
            raise ValueError(action)
        if len(args) != 1:
            raise ValueError(args)
        calls = args[0]
        response = []
        for call in calls:
            method_name = call['methodName']
            if method_name in self.results:
                result = self.results[method_name]
                response.append([result])
            else:
                result = {'faultNumber': 1000,
                          'faultString': 'Invalid method: %s' % method_name}
                response.append(result)
        return defer.succeed(response)


@pytest.fixture
def koji(monkeypatch):
    monkeypatch.setattr('txkoji.connection.Proxy', FakeProxy)
    koji = Connection('mykoji')
    return koji


@pytest_twisted.inlineCallbacks
def test_multicall(koji):
    multicall = koji.MultiCall()
    multicall.getAPIVersion()
    results = yield multicall()
    assert list(results) == [1]


@pytest_twisted.inlineCallbacks
def test_multicall_error(koji):
    # Test one good call, and one bad call, and the iterator should raise on
    # the bad call, just like the normal XML-RPC client.
    multicall = koji.MultiCall()
    multicall.getAPIVersion()
    multicall.nonExistantMethod()
    results = yield multicall()
    resultsiter = iter(results)
    assert next(resultsiter) == 1
    with pytest.raises(KojiException):
        next(resultsiter)


@pytest_twisted.inlineCallbacks
def test_multicall_type(koji):
    multicall = koji.MultiCall()
    multicall.getTaskInfo(12345)
    results = yield multicall()
    result = next(iter(results))
    # Ensure this is a Task instance, not a generic Munch instance:
    assert isinstance(result, Task)
    # Verify the contents:
    assert isinstance(result.connection, Connection)
    assert result.id == 12345
    assert result.method == 'tagBuild'
