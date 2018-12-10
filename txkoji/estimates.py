from datetime import timedelta
from txkoji import build_states
from twisted.internet import defer


"""
Methods for estimating build times.
"""


def average_build_duration(connection, package):
    """
    Return the average build duration for a package (or container).

    :param connection: txkoji.Connection
    :param package: package name
    :returns: deferred that when fired returns a datetime.timedelta object
    """
    if package.endswith('-container'):
        return average_last_builds(connection, package)
    return connection.getAverageBuildDuration(package)


def average_build_durations(connection, packages):
    """
    Return the average build duration for a package (or container).

    :param connection: txkoji.Connection
    :param list packages: package names
    :returns: deferred that when fired returns a list of timdelta objects
    """
    deferreds = [average_build_duration(connection, pkg) for pkg in packages]
    return defer.gatherResults(deferreds, consumeErrors=True)


@defer.inlineCallbacks
def average_last_builds(connection, package, limit=5):
    """
    Find the average duration time for the last couple of builds.

    :param connection: txkoji.Connection
    :param package: package name
    :returns: deferred that when fired returns a datetime.timedelta object, or
              None if there were no previous builds for this package.
    """
    # TODO: take branches (targets, or tags, etc) into account when estimating
    # a package's build time.
    state = build_states.COMPLETE
    opts = {'limit': limit, 'order': '-completion_time'}
    builds = yield connection.listBuilds(package, state=state, queryOpts=opts)
    if not builds:
        defer.returnValue(None)
    durations = [build.duration for build in builds]
    average = sum(durations, timedelta()) / len(durations)
    # print('average duration for %s is %s' % (package, average))
    defer.returnValue(average)
