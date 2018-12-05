from datetime import datetime, timedelta
from txkoji import Connection
from txkoji import task_states
from txkoji import build_states
from twisted.internet import defer
from twisted.internet.task import react

# Estimate a buildContainer task's completion time.


@defer.inlineCallbacks
def example(reactor):
    koji = Connection('brew')

    # Look up the task information:
    task = yield koji.getTaskInfo(18792505)
    assert task.method == 'buildContainer'

    if task.state == task_states.FREE:
        yield estimate_free(koji, task)
    elif task.state == task_states.OPEN:
        yield estimate_open(koji, task)
    else:
        print('final duration: %s' % task.duration)


@defer.inlineCallbacks
def estimate_free(koji, task):
    # Look up how many tasks are ahead of this one.
    channel_id = task.channel_id
    free_tasks = yield list_free_tasks(koji, channel_id)
    ahead = []
    for free_task in free_tasks:
        if task.id > free_task.id:
            ahead.append(free_task)
    print('There are %d free buildContainer tasks ahead of this one' %
          len(ahead))
    # Note:
    # If there is more capacity available than total outstanding buildContainer
    # FREE tasks, then either the system is hung, *or* (more likely) a builder
    # is about to pick this one up in the next few seconds. If this
    # task.duration < 60 seconds, then the latter is likely. While we wait for
    # the builder to pick it up, we could tack on an additional 60 seconds and
    # then estimate based on that.
    capacity = yield total_capacity(koji, channel_id)
    print('This channel can handle %d tasks at a time' % capacity)


@defer.inlineCallbacks
def estimate_open(koji, task):
    # TODO: take branches into account when estimating a task.
    # - Look at this build target, determine the destination tag, and then list
    #   the 10 most recent builds that are tagged into that destination.
    #   Average the duration for that list of builds.
    # - If we could not find anything tagged into that destination yet, fall
    #   back to simply searching the 10 most recent build overall and averaging
    #   those build's durations.
    # - If there is no recent build (it's an entirely new package), return
    #   None.
    duration = yield average_build_duration(koji, task.package)
    est_complete = task.started + duration
    remaining = est_complete - datetime.utcnow()
    description = describe_delta(remaining)
    if remaining.total_seconds() > 0:
        print('this task should be complete in %s' % description)
    else:
        print('this task exceeds the last build by %s' % description)


@defer.inlineCallbacks
def average_build_duration(koji, package, limit=5):
    """
    Find the average duration time for the last couple of builds.

    :returns: deferred that when fired returns a datetime.timedelta object
    """
    state = build_states.COMPLETE
    opts = {'limit': 5, 'order': '-completion_time'}
    print('Looking for previous %s builds' % package)
    builds = yield koji.listBuilds(package, state=state, queryOpts=opts)
    durations = [build.duration for build in builds]
    average = sum(durations, timedelta()) / limit
    print('average duration is %s' % average)
    defer.returnValue(average)


def list_free_tasks(koji, channel_id):
    """
    List all the not-yet-started tasks for this channel

    :returns: deferred that when fired returns a list of tasks
    """
    # state_names = ['FREE', 'ASSIGNED']
    # states = [getattr(task_states, name) for name in state_names]
    state = getattr(task_states, 'FREE')
    opts = {'state': [state], 'channelID': channel_id}
    qopts = {'order': 'priority,create_time'}
    return koji.listTasks(opts, qopts)


@defer.inlineCallbacks
def total_capacity(koji, channel_id):
    """
    Look up the current capacity for this channel.
    """
    total_capacity = 0
    hosts = yield koji.listHosts(channelID=channel_id, enabled=True)
    for host in hosts:
        total_capacity += host.capacity
    defer.returnValue(total_capacity)


def describe_delta(delta):
    """
    Describe this timedelta in human-readable terms.

    :param delta: datetime.timedelta object
    :returns: str, describing this delta
    """
    s = delta.total_seconds()
    s = abs(s)
    hours, remainder = divmod(s, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return '%d hr %d min' % (hours, minutes)
    if minutes:
        return '%d min %d secs' % (minutes, seconds)
    return '%d secs' % seconds


if __name__ == '__main__':
    react(example)
