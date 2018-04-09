from twisted.web.xmlrpc import _QueryFactory, payloadTemplate
from twisted.python.compat import unicode
from twisted.internet import defer
from txkoji.marshaller import KojiMarshaller


class KojiQueryFactory(_QueryFactory):
    def __init__(self, path, host, method, user=None, password=None,
                 allowNone=True, args=(), canceller=None, useDateTime=False):
        """
        Mainly copied from Twisted's _QueryFactory class, except we use our own
        KojiMarshaller instead of stdlib's xmlrpc Marshaller.
        """
        self.path, self.host = path, host
        self.user, self.password = user, password
        self.marshaller = KojiMarshaller('utf-8', allow_none=True)
        self.payload = payloadTemplate \
            % (method, self.marshaller.dumps(args))
        if isinstance(self.payload, unicode):
            self.payload = self.payload.encode('utf-8')
        self.deferred = defer.Deferred(canceller)
        self.useDateTime = useDateTime
        # Debug the client's XML-RPC payload:
        # print(self.payload)

    # def parseResponse(self, contents):
    #     """ Debugging: print the server's response to STDOUT. """
    #     print(contents)
    #     return _QueryFactory.parseResponse(self, contents)
