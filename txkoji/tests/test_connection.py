import pytest
from txkoji.connection import Connection
from txkoji.build import Build
from txkoji.tests.util import FakeProxy


def test_basic():
    koji = Connection('mykoji')
    assert koji
    assert koji.url == 'https://hub.example.com/kojihub'


def test_missing_profile(monkeypatch):
    monkeypatch.setattr('txkoji.connection.PROFILES', ['/noexist'])
    with pytest.raises(ValueError):
        Connection('mykoji')


def bad_web_url_matrix():
    """
    Return a list of bad inputs to "from_web" methods.

    connect_from_web() and from_web() should return None with these inputs.
    """
    buildurl = 'https://koji.example.com/koji/buildinfo?buildID=24284'
    strings = [
        'foobar',
        'https://koji.example.com',
        'check out %s' % buildurl,
        '%s is cool' % buildurl,
        'please check %s now' % buildurl
    ]
    return strings


class TestConnectFromWeb(object):

    def test_good(self, ):
        teststr = 'https://koji.example.com/koji/buildinfo?buildID=24284'
        koji = Connection.connect_from_web(teststr)
        assert isinstance(koji, Connection)
        assert koji.url == 'https://hub.example.com/kojihub'

    @pytest.mark.parametrize('teststr', bad_web_url_matrix())
    def test_bad(self, teststr):
        koji = Connection.connect_from_web(teststr)
        assert koji is None


class TestFromWeb(object):

    @pytest.inlineCallbacks
    def test_good(self, monkeypatch):
        # To create this fixture file:
        # cbs call getBuild 24284 \
        #   --json-output > txkoji/tests/fixtures/calls/getBuild.json
        monkeypatch.setattr('txkoji.connection.Proxy', FakeProxy)
        teststr = 'https://koji.example.com/koji/buildinfo?buildID=24284'
        koji = Connection('mykoji')
        build = yield koji.from_web(teststr)
        assert isinstance(build, Build)
        assert build.id == 24284

    @pytest.inlineCallbacks
    @pytest.mark.parametrize('teststr', bad_web_url_matrix())
    def test_bad(self, monkeypatch, teststr):
        monkeypatch.setattr('txkoji.connection.Proxy', FakeProxy)
        koji = Connection('mykoji')
        resource = yield koji.from_web(teststr)
        assert resource is None

    @pytest.inlineCallbacks
    def test_malformed(self, monkeypatch):
        monkeypatch.setattr('txkoji.connection.Proxy', FakeProxy)
        teststr = 'https://koji.example.com/koji/buildinfo?buildID=24284whoops'
        koji = Connection('mykoji')
        resource = yield koji.from_web(teststr)
        assert resource is None
