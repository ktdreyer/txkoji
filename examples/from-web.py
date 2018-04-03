from txkoji import Connection, KojiException
from twisted.internet import defer, reactor


@defer.inlineCallbacks
def example():
    url = 'https://cbs.centos.org/koji/buildinfo?buildID=21155'
    koji = Connection.connect_from_web(url)
    try:
        data = yield koji.from_web(url)
        print(data)
    except KojiException as e:
        print(type(e))
        print(e)
    except Exception as e:
        print(type(e))
        print(e)


if __name__ == '__main__':
    d = example()
    d.addCallback(lambda ign: reactor.stop())
    d.addErrback(lambda ign: reactor.stop())
    reactor.run()
