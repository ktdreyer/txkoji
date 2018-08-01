from txkoji import Connection
from twisted.internet import defer
from twisted.internet.task import react


@defer.inlineCallbacks
def example(reactor):
    url = 'https://cbs.centos.org/koji/buildinfo?buildID=21155'
    koji = Connection.connect_from_web(url)
    if not koji:
        raise ValueError('url %s is not a recognizable Koji URL' % url)
    data = yield koji.from_web(url)
    print(data)


if __name__ == '__main__':
    react(example)
