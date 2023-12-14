from operator import itemgetter
from datetime import datetime, timedelta, UTC
import sys
from txkoji import Connection
from txkoji import task_states
from txkoji.estimates import average_build_duration
from txkoji.estimates import average_build_durations
from twisted.internet import defer
from twisted.internet.task import react

# Estimate a buildContainer task's completion time.


@defer.inlineCallbacks
def example(reactor):
    task_id = sys.argv[1]
    koji = Connection('brew')

    # Look up the task information:
    task = yield koji.getTaskInfo(task_id)

    if task.state == task_states.FREE:
        # we'll wrap task.estimate_completion in estimate_free() below:
        # est_complete = yield task.estimate_completion()
        est_complete = yield estimate_free(koji, task)
        log_est_complete(est_complete)
    elif task.state == task_states.OPEN:
        est_complete = yield task.estimate_completion()
        log_est_complete(est_complete)
    else:
        log_delta('final duration: %s', task.duration)


@defer.inlineCallbacks
def estimate_free(koji, task):
    try:
        # Test our new "free" code:
        est_completion = yield task.estimate_completion()
        if not est_completion:
            err = 'could not estimate with task.estimate_completion()'
            raise RuntimeError(err)
        defer.returnValue(est_completion)
    except NotImplementedError:
        pass  # channel at capacity
    print('channel %d is at capacity' % task.channel_id)
    # From this point on, we assume that all the OPEN tasks are going to be
    # faster than the fastest FREE tasks that are still in the queue. If this
    # is not the case, then our estimate will be longer than reality.

    # See how many packages are ahead of us in the queue.
    ahead_free = yield task.channel.tasks(state=[task_states.FREE],
                                          createdBefore=task.create_ts)
    print('%d tasks are in FREE state ahead of us' % len(ahead_free))
    ahead_weight = sum([task.weight for task in ahead_free])
    print('the total weight of the ahead FREE tasks is %s' % ahead_weight)

    # Calculate the average durations for all OPEN "packages".
    open_estimates = yield task_estimates(task.channel, [task_states.OPEN])

    # Sort by time remaining:
    sorted_estimates = sorted(open_estimates, key=itemgetter(1))

    # Find the "longest" task until we get to our desired weight_count.
    longest = timedelta(0)
    weight_count = 0
    for task, longest in sorted_estimates:
        weight_count += task.weight
        # In "longest" time, we will have "weight_count" free.
        if weight_count >= ahead_weight:
            break
    log_delta('Longest OPEN task estimate until we get to OPEN: %s', longest)

    avg_duration = yield average_build_duration(koji, task.package)
    remaining = longest + avg_duration
    est_complete = datetime.now(UTC) + remaining
    defer.returnValue(est_complete)


@defer.inlineCallbacks
def task_estimates(channel, states):
    """
    Estimate remaining time for all tasks in this channel.

    :param channel: txkoji.channel.Channel
    :param list states: list of task_states ints, eg [task_states.OPEN]
    :returns: deferred that when fired returns a list of
              (task, est_remaining) tuples
    """
    for state in states:
        if state != task_states.OPEN:
            raise NotImplementedError('only estimate OPEN tasks')
    tasks = yield channel.tasks(state=states)
    # Estimate all the unique packages.
    packages = set([task.package for task in tasks])
    print('checking avg build duration for %i packages:' % len(packages))
    packages = list(packages)
    durations = yield average_build_durations(channel.connection, packages)
    avg_package_durations = dict(zip(packages, durations))
    # pprint(avg_package_durations)
    # Determine estimates for all our tasks.
    results = []
    utcnow = datetime.now(UTC)
    for task in tasks:
        avg_duration = avg_package_durations[task.package]
        est_complete = task.started + avg_duration
        est_remaining = est_complete - utcnow
        result = (task, est_remaining)
        results.append(result)
    defer.returnValue(results)


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


def log_est_complete(est_complete):
    """
    Log the relative time remaining for this est_complete datetime object.
    """
    if not est_complete:
        print('could not determine an estimated completion time')
        return
    remaining = est_complete - datetime.now(UTC)
    message = 'this task should be complete in %s'
    if remaining.total_seconds() < 0:
        message = 'this task exceeds estimate by %s'
    log_delta(message, remaining)


def log_delta(message, delta, *args):
    description = describe_delta(delta)
    format_args = list(args)
    format_args.insert(0, description)
    print(message % tuple(format_args))


if __name__ == '__main__':
    react(example)
