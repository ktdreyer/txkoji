from twisted.web.xmlrpc import Proxy
from twisted.web.xmlrpc import QueryProtocol
from twisted.internet import error
from twisted.internet import ssl
from twisted.python.compat import nativeString


"""
In Twisted prior to 20.11.0, the Twisted XML-RPC client did not do any HTTPS
server cert verification (https://twistedmatrix.com/trac/ticket/9836).

In Twisted 20.11.0 and later, the Twisted XML-RPC verifies the HTTPS server
cert against the system-wide bundle, but there is no way to verify against a
specific CA.

The subclasses within this module verify the HTTPS cert against the
system-wide CA bundle (default) or a specific CA.
"""


class ErrorCheckingQueryProtocol(QueryProtocol):
    """
    Adds additional error checking in connectionLost

    https://twistedmatrix.com/pipermail/twisted-python/2016-June/030466.html

    This functionality is built into Twisted upstream in 20.11.0 and later,
    https://twistedmatrix.com/trac/ticket/9836.
    This subclass backports the feature for earlier Twisted versions.
    """
    def connectionLost(self, reason):
        if not reason.check(error.ConnectionDone, error.ConnectionLost):
            # for example, ssl.SSL.Error
            self.factory.clientConnectionLost(None, reason)
        super(ErrorCheckingQueryProtocol, self).connectionLost(reason)


class TrustedProxy(Proxy, object):
    """
    twisted.web.xmlrpc.Proxy subclass that can do SSL verification
    """
    def __init__(self, *args, **kwargs):
        """
        This constructor takes a new "trustRoot" kwarg. We pass this
        trustRoot to twisted.internet.ssl.optionsForClientTLS().

        :param IOpenSSLTrustRoot trustRoot:
            See the optionsForClientTLS documentation. To trust a single CA
            (in a pem file format on disk), you can pass the result of
            ssl.Certificate.loadPEM() here. If you set trustRoot to None (the
            default), we use the result of ssl.platformTrust(), which means we
            validate the connection against the system-wide CA bundle.
        """
        trustRoot = kwargs.pop('trustRoot', None)
        # Update our QueryProtocol to raise ssl.SSL.Error rather than skipping
        # it:
        self.queryFactory.protocol = ErrorCheckingQueryProtocol
        super(TrustedProxy, self).__init__(*args, **kwargs)

    def callRemote(self, method, *args):
        if not self.secure:
            # Parent behavior is fine
            # (Will this work on our old-style class on py2?)
            return super(TrustedProxy, self).callRemote(method, *args)

        # Copying the rest from the Proxy class in Twisted's xmlrpc.py here:

        def cancel(d):
            factory.deferred = None
            connector.disconnect()

        factory = self.queryFactory(
            self.path, self.host, method, self.user,
            self.password, self.allowNone, args, cancel, self.useDateTime)

        contextFactory = ssl.optionsForClientTLS(
            hostname=nativeString(self.host),
            trustRoot=self.trustRoot)

        connector = self._reactor.connectSSL(
            nativeString(self.host), self.port or 443,
            factory, contextFactory,
            timeout=self.connectTimeout)

        return factory.deferred
