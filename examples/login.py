from txkoji import Connection
from twisted.internet import defer
from twisted.internet.task import react


@defer.inlineCallbacks
def example(reactor):
    koji = Connection('fedora')
    #koji = Connection('cbs')
    # Attempt to log in
    result = yield koji.login()
    print('logged in: %s' % result)
    print('session-id: %s' % koji.session_id)
    user = yield koji.getLoggedInUser()
    print(user)


if __name__ == '__main__':
    react(example)
