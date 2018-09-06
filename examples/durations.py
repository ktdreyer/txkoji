from txkoji import Connection
from twisted.internet import defer
from twisted.internet.task import react
from pprint import pprint


@defer.inlineCallbacks
def describe_task(koji, task_id):
    task = yield koji.getTaskInfo(task_id)
    # Find the buildArch child tasks.
    subtasks = yield task.descendents(method='buildArch')
    owner_name = yield koji.cache.user_name(task.owner)
    print(task.url)
    print('package: %s' % task.package)
    print('owner: %s' % owner_name)
    print('target: %s' % task.target)
    print('is_scratch: %s' % task.is_scratch)
    for subtask in subtasks:
        print('buildArch(%s): %s' % (subtask.arch, subtask.duration))
    print('-----------------------')


@defer.inlineCallbacks
def example(reactor):
    koji = Connection('brew')
    # Compare two ceph build tasks:
    yield describe_task(koji, 18117489)  # without 'make check'
    yield describe_task(koji, 18199887)  # with 'make check'


if __name__ == '__main__':
    react(example)
