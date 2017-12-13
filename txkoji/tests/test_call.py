from munch import Munch
import pytest
from txkoji import Connection
from twisted.internet import defer


class _StubProxy(object):
    def __init__(self, url, **kwargs):
        pass

    def callRemote(self, action, payload):
        """ Return a deferred that always fires successfully """
        assert action == 'getUser'
        result = {'id': 2826,
                  'krb_principal': 'kdreyer@EXAMPLE.COM',
                  'name': 'kdreyer',
                  'status': 0,
                  'usertype': 0}
        return defer.succeed(result)


class TestCall(object):

    @pytest.inlineCallbacks
    def test_getuser(self, monkeypatch):
        monkeypatch.setattr('txkoji.Proxy', _StubProxy)
        koji = Connection('mykoji')
        user = yield koji.getUser('kdreyer')
        expected = Munch(id=2826,
                         krb_principal='kdreyer@EXAMPLE.COM',
                         name='kdreyer',
                         status=0,
                         usertype=0)
        assert user == expected
