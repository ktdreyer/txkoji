from datetime import datetime, timedelta
from munch import Munch
import pytest
from txkoji import Connection
from txkoji import task_states
from txkoji.task import Task
from txkoji.tests.util import FakeProxy
import pytest_twisted


class TestGetTask(object):

    @pytest.fixture
    def task(self, monkeypatch):
        # To create this fixture file:
        # cbs call getTaskInfo 291929 --kwargs="{'request': True}" \
        #   --json-output > txkoji/tests/fixtures/calls/getTaskInfo.json
        monkeypatch.setattr('txkoji.connection.Proxy', FakeProxy)
        koji = Connection('mykoji')
        d = koji.getTaskInfo(291929)
        return pytest_twisted.blockon(d)

    def test_type(self, task):
        assert isinstance(task, Task)

    def test_state(self, task):
        assert task.state == task_states.CLOSED

    def test_duration(self, task):
        assert task.duration == timedelta(0, 138, 577600)

    def test_package(self, task):
        assert task.package == 'ceph-ansible'

    def test_url(self, task):
        expected = 'https://koji.example.com/koji/taskinfo?taskID=291929'
        assert task.url == expected

    def test_is_scratch(self, task):
        assert task.is_scratch is False

    @pytest.inlineCallbacks
    def test_estimate_completion(self, task):
        est_completion = yield task.estimate_completion()
        # Since this build has finished, the estimate_completion() method
        # should simply return the real completed datetime.
        expected = datetime(2018, 1, 12, 16, 18, 43, 236640)
        assert est_completion == expected
        assert est_completion == task.completed


class TestListTasks(object):

    @pytest.fixture
    def tasks(self, monkeypatch):
        # To create this fixture file:
        # cbs call listTasks --kwargs="{'opts': {'owner': 144, 'method': 'build', 'decode': True}}" --json-output > txkoji/tests/fixtures/calls/listTasks.json  # NOQA: E501
        monkeypatch.setattr('txkoji.connection.Proxy', FakeProxy)
        koji = Connection('mykoji')
        opts = {'owner': 144, 'method': 'build'}
        d = koji.listTasks(opts)
        return pytest_twisted.blockon(d)

    def test_value_is_list(self, tasks):
        assert isinstance(tasks, list)

    def test_list_length(self, tasks):
        assert len(tasks) > 0

    def test_list_types(self, tasks):
        for task in tasks:
            assert isinstance(task, Munch)
            assert isinstance(task, Task)

    def test_first_task(self, tasks):
        task = tasks[0]
        assert task.state == task_states.FAILED
