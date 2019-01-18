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
    if isinstance(package, str) and package.endswith('-container'):
        return average_last_builds(connection, package)
    return connection.getAverageBuildDuration(package)


@defer.inlineCallbacks
def average_build_durations(connection, packages):
    """
    Return the average build duration for list of packages (or containers).

    :param connection: txkoji.Connection
    :param list packages: package names. These must all be containers, or they
                          must all be RPMs (do not mix and match.)
    :returns: deferred that when fired returns a KojiMultiCallIterator, which
              has a list of timdelta objects.
    """
    containers = [name for name in packages if name.endswith('-container')]
    if len(containers) == len(packages):
        containers = True
    elif len(containers) == 0:
        containers = True
    else:
        # This is going to be too complicated to do with multicalls.
        raise NotImplementedError('cannot mix containers and non-containers')

    if not containers:
        multicall = connection.MultiCall()
        for name in packages:
            multicall.getPackage(name)
        multicall.getAverageBuildDuration(name)
        result = yield multicall()
        defer.returnValue(result)

    # Map all container names to packages (IDs).
    multicall = connection.MultiCall()
    names = set(packages)
    for name in names:
        multicall.getPackage(name)
    results = yield multicall()
    package_map = dict(zip(names, results))

    # List the previous builds for each container.
    state = build_states.COMPLETE
    opts = {'limit': 5, 'order': '-completion_time'}
    multicall = connection.MultiCall()
    built_packages = []
    for name in names:
        package = package_map[name]
        if package:
            built_packages.append(name)
            multicall.listBuilds(package.id, state=state, queryOpts=opts)
    results = yield multicall()
    builds_map = dict(zip(built_packages, results))

    package_durations = []
    for name in packages:
        builds = builds_map.get(name)
        average = None
        if builds:
            durations = [build.duration for build in builds]
            average = sum(durations, timedelta()) / len(durations)
        package_durations.append(average)
    defer.returnValue(package_durations)


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
