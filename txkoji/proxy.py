from twisted.web.xmlrpc import Proxy
from twisted.web.xmlrpc import QueryProtocol
from twisted.internet import error
from twisted.internet import ssl
from twisted.python.compat import nativeString


"""
Twisted's XML-RPC client does not do HTTPS cert verification by default,
https://twistedmatrix.com/trac/ticket/9836

The subclasses within this module verify the HTTPS cert against the
system-wide CA bundle (default) or a specific CA.
"""


class ErrorCheckingQueryProtocol(QueryProtocol):
    """
    Adds additional error checking in connectionLost

    https://twistedmatrix.com/pipermail/twisted-python/2016-June/030466.html
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
        # We have just called the constructor without a trustRoot kwarg. In
        # the event that https://github.com/twisted/twisted/pull/1287 merges
        # upstream, self.trustRoot will always be None. In order to be
        # compatible with that PR, we must assign self.trustRoot here after
        # we've called the constructor.
        self.trustRoot = trustRoot

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
