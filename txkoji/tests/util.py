from twisted.web.xmlrpc import Proxy
from twisted.internet import defer
import json
import os

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(TESTS_DIR, 'fixtures')


class FakeProxy(Proxy):
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


class FakeSSLLoginResponse(object):
    """ Fake response from treq, for testing HTTP login """
    def __init__(self, url, code=200):
        self.url = url
        self.code = code

    def content(self):
        assert 'ssllogin' in self.url
        if self.code == 200:
            filename = 'ssllogin/sslLogin.xml'
            fixture = os.path.join(FIXTURES_DIR, 'requests', filename)
            with open(fixture, 'rb') as fp:
                result = fp.read()
            return defer.succeed(result)
        return defer.succeed(b'HTTP error')
