import pytest
from twisted.internet import defer
from txkoji import Connection
from txkoji import KojiGssapiException
from txkoji.tests.util import FakeSSLLoginResponse


def fake_post_ok(url, data=None, **kwargs):
    """ Fake treq_kerberos.post """
    response = FakeSSLLoginResponse(url)
    return defer.succeed(response)


def fake_post_unauthorized(url, data=None, **kwargs):
    """ Fake treq_kerberos.post """
    response = FakeSSLLoginResponse(url, code=401)
    return defer.succeed(response)


class TestLogin(object):

    @pytest.inlineCallbacks
    def test_login_success(self, monkeypatch):
        monkeypatch.setattr('treq_kerberos.post', fake_post_ok)
        koji = Connection('mykoji')
        result = yield koji.login()
        assert result is True
        assert koji.session_id == 12345678
        assert koji.session_key == '1234-abcdefghijklmnopqrst'

    @pytest.inlineCallbacks
    def test_login_failure(self, monkeypatch):
        monkeypatch.setattr('treq_kerberos.post', fake_post_unauthorized)
        koji = Connection('mykoji')
        with pytest.raises(KojiGssapiException):
            yield koji.login()
