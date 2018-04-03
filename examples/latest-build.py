from txkoji import Connection, KojiException
from twisted.internet import defer, reactor


@defer.inlineCallbacks
def example():
    koji = Connection('brew')
    # Fetch the five latest ceph builds
    try:
        # "order: -build_id" will list the newest (build timestamp) ones first.
        opts = {'limit': 5, 'order': '-build_id'}
        # set "state" to txkoji.build_states.RUNNING here to filter further.
        builds = yield koji.listBuilds('ceph', state=None, queryOpts=opts)
        # builds are Munch (dict-like) objects.
        for build in builds:
            print(build.nvr)
            print(build.state)
    except KojiException as e:
        print(e)
    except Exception as e:
        print(type(e))
        print(e)


if __name__ == '__main__':
    d = example()
    d.addCallback(lambda ign: reactor.stop())
    d.addErrback(lambda ign: reactor.stop())
    reactor.run()
