from txkoji import Connection
from twisted.internet import defer
from twisted.internet.task import react


@defer.inlineCallbacks
def example(reactor):
    koji = Connection('fedora')
    name = yield koji.cache.tag_name(197)
    # "rawhide"
    print('tag name: %s' % name)


if __name__ == '__main__':
    react(example)
