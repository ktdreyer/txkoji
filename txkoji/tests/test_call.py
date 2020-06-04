from munch import Munch
import pytest_twisted
from txkoji.connection import Connection
from txkoji.tests.util import FakeProxy


class TestCall(object):

    @pytest_twisted.inlineCallbacks
    def test_getuser(self, monkeypatch):
        # brew call getUser kdreyer@REDHAT.COM \
        #   --json-output > txkoji/tests/fixtures/calls/getUser.json
        monkeypatch.setattr('txkoji.connection.TrustedProxy', FakeProxy)
        koji = Connection('mykoji')
        user = yield koji.getUser('kdreyer')
        expected = Munch(id=2826,
                         krb_principal='kdreyer@EXAMPLE.COM',
                         name='kdreyer',
                         status=0,
                         usertype=0)
        assert user == expected
