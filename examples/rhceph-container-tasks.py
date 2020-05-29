from txkoji import Connection
from txkoji import task_states
from twisted.internet import defer
from twisted.internet.task import react

"""
Find all the free and open tasks for the rhceph-container package.
"""


@defer.inlineCallbacks
def example(reactor):
    koji = Connection('brew')
    channel = yield koji.getChannel('container')
    print('channel: %s' % channel)
    print('name: %s' % channel.name)
    tasks = yield channel.tasks(state=[task_states.FREE, task_states.OPEN])
    if not tasks:
        raise ValueError('no open tasks for this channel')
    for task in iter(tasks):
        if task.package == 'rhceph-container':
            print(task.url)


if __name__ == '__main__':
    react(example)
