from twisted.internet import defer
import json
import os

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(TESTS_DIR, 'fixtures')


class StubProxy(object):
    def __init__(self, url, **kwargs):
        pass

    def callRemote(self, action, *args):
        """ Return a deferred that always fires successfully """
        filename = action + '.json'
        fixture = os.path.join(FIXTURES_DIR, 'calls', filename)
        try:
            with open(fixture) as fp:
                result = json.load(fp)
        except IOError:
            print('Create new fixture file at %s' % fixture)
            print('koji call %s ... --json-output > %s' % (action, fixture))
            raise
        return defer.succeed(result)
