from txkoji import Connection
from twisted.internet import defer
from twisted.internet.task import react


@defer.inlineCallbacks
def example(reactor):
    koji = Connection('brew')
    # Fetch the five latest ceph builds
    # "order: -build_id" will list the newest (build timestamp) ones first.
    opts = {'limit': 5, 'order': '-build_id'}
    # set "state" to txkoji.build_states.RUNNING here to filter further.
    builds = yield koji.listBuilds('ceph', state=None, queryOpts=opts)
    # builds are Munch (dict-like) objects.
    for build in builds:
        print(build.nvr)
        print(build.state)


if __name__ == '__main__':
    react(example)
