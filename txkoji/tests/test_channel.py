import pytest
from txkoji import Connection
from txkoji.channel import Channel
from txkoji.tests.util import FakeProxy
import pytest_twisted


class TestGetChannel(object):

    @pytest.fixture
    def channel(self, monkeypatch):
        # To create this fixture file:
        # cbs call getChannel 2 \
        #   --json-output > txkoji/tests/fixtures/calls/getChannel.json
        monkeypatch.setattr('txkoji.connection.Proxy', FakeProxy)
        koji = Connection('mykoji')
        d = koji.getChannel(2)
        return pytest_twisted.blockon(d)

    def test_type(self, channel):
        assert isinstance(channel, Channel)

    def test_id(self, channel):
        assert channel.id == 2

    def test_name(self, channel):
        assert channel.name == 'createrepo'

    def test_connection(self, channel):
        assert isinstance(channel.connection, Connection)

    @pytest.inlineCallbacks
    def test_hosts(self, channel):
        hosts = yield channel.hosts(enabled=True)
        expected = [
            {'arches': 'x86_64 i386',
             'capacity': 16.0,
             'comment': None,
             'description': None,
             'enabled': True,
             'id': 1,
             'name': 'x86_64-0.centos.org',
             'ready': True,
             'task_load': 0.0,
             'user_id': 7},
            {'arches': 'x86_64 i386',
             'capacity': 30.0,
             'comment': None,
             'description': None,
             'enabled': True,
             'id': 3,
             'name': 'x86_64-2.cbs.centos.org',
             'ready': True,
             'task_load': 0.0,
             'user_id': 49}
         ]
        assert hosts == expected


class TestListChannels(object):

    @pytest.fixture
    def channels(self, monkeypatch):
        # To create this fixture file:
        # cbs call listChannels \
        #   --json-output > txkoji/tests/fixtures/calls/listChannels.json
        monkeypatch.setattr('txkoji.connection.Proxy', FakeProxy)
        koji = Connection('mykoji')
        d = koji.listChannels()
        return pytest_twisted.blockon(d)

    def test_type(self, channels):
        assert isinstance(channels, list)

    def test_expected(self, channels):
        channel = channels[0]
        assert channel.id == 1
        assert channel.name == 'default'
        assert isinstance(channel.connection, Connection)
