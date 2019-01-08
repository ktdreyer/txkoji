from datetime import datetime, timedelta
import pytest
from txkoji import Connection
from txkoji import build_states
from txkoji.build import Build
from txkoji.tests.util import FakeProxy
import pytest_twisted


class TestGetBuild(object):

    @pytest.fixture
    def build(self, monkeypatch):
        # To create this fixture file:
        # cbs call getBuild 24284 \
        #   --json-output > txkoji/tests/fixtures/calls/getBuild.json
        monkeypatch.setattr('txkoji.connection.Proxy', FakeProxy)
        koji = Connection('mykoji')
        d = koji.getBuild(24284)
        return pytest_twisted.blockon(d)

    def test_type(self, build):
        assert isinstance(build, Build)

    def test_state(self, build):
        assert build.state == build_states.COMPLETE

    def test_duration(self, build):
        assert build.duration == timedelta(0, 139, 239820)

    def test_package_name(self, build):
        assert build.package_name == 'ceph-ansible'

    def test_url(self, build):
        expected = 'https://koji.example.com/koji/buildinfo?buildID=24284'
        assert build.url == expected

    def test_gitbuildhash(self, build):
        # TODO: test with a build fixture where we have a real source URL
        assert build.gitbuildhash is None

    @pytest_twisted.inlineCallbacks
    def test_estimate_completion(self, build):
        est_completion = yield build.estimate_completion()
        # Since this build has finished, the estimate_completion() method
        # should simply return the real completed datetime.
        expected = datetime(2018, 9, 26, 13, 59, 43, 905240)
        assert est_completion == expected
        assert est_completion == build.completed
