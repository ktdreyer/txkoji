from datetime import datetime, timedelta
import sys
from txkoji import Connection
from txkoji import task_states
from txkoji import build_states
from twisted.internet import defer
from twisted.internet.task import react

# Estimate a buildContainer task's completion time.


@defer.inlineCallbacks
def example(reactor):
    task_id = sys.argv[1]
    koji = Connection('brew')

    # Look up the task information:
    task = yield koji.getTaskInfo(task_id)
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
    free_tasks = yield list_tasks(koji, channel_id, 'FREE')
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
    # From this point on, we assume that all the OPEN tasks are going to be
    # faster than the fastest FREE tasks that are still in the queue. If this
    # is not the case, then our estimate will be longer than reality.
    # Estimate the duration of each open task.
    open_tasks = yield list_tasks(koji, channel_id, 'OPEN')
    avg_durations = {}
    open_estimates = []
    utcnow = datetime.utcnow()
    for open_task in open_tasks:
        if open_task.method != 'buildContainer':
            raise RuntimeError('%s is not buildContainer' % open_task.url)
        package = open_task.package
        duration = avg_durations.get(package)
        if not duration:
            duration = yield average_build_duration(koji, package)
            avg_durations[package] = duration
        est_complete = open_task.started + duration
        remaining = est_complete - utcnow
        open_estimates.append(remaining)
    # Sort by estimated completion:
    sorted_estimates = sorted(open_estimates)
    # Find the "ahead" number (eg. "10") shortest tasks.
    ahead_estimates = sorted_estimates[:len(ahead)]
    # The longest of that number is how long we have to wait to get to OPEN.
    longest = ahead_estimates[-1]
    print('The longest OPEN task until we get to OPEN: %s' % longest)
    avg_duration = yield average_build_duration(koji, task.package)
    remaining = longest + avg_duration
    description = describe_delta(remaining)
    print('Our task should be complete in %s' % description)


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
    builds = yield koji.listBuilds(package, state=state, queryOpts=opts)
    durations = [build.duration for build in builds]
    average = sum(durations, timedelta()) / limit
    print('average duration for %s is %s' % (package, average))
    defer.returnValue(average)


def list_tasks(koji, channel_id, state_name):
    """
    List all the tasks for this channel

    :param: state_name: eg "FREE"
    :returns: deferred that when fired returns a list of tasks
    """
    # state_names = ['FREE', 'ASSIGNED']
    # states = [getattr(task_states, name) for name in state_names]
    state = getattr(task_states, state_name)
    opts = {'state': [state], 'channel_id': channel_id}
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
