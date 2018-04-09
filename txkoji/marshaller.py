from twisted.python.compat import long
try:
    import xmlrpc
    from xmlrpc.client import Marshaller
except ImportError:
    import xmlrpclib as xmlrpc
    from xmlrpclib import Marshaller


class KojiMarshaller(Marshaller):
    """ Custom XML-RPC Marshaller for long ints. """
    dispatch = Marshaller.dispatch.copy()

    MAXI8 = 2 ** 63 - 1
    MINI8 = -2 ** 63

    def dump_int(self, value, write):
        if (value > self.MAXI8 or value < self.MINI8):
            raise OverflowError("long int exceeds XML-RPC limits")
        elif value > xmlrpc.MAXINT or value < xmlrpc.MININT:
            write("<!-- using i8 extension -->")
            write("<value><i8>")
            write(str(int(value)))
            write("</i8></value>\n")
        else:
            return Marshaller.dump_int(self, value, write)

    dispatch[int] = dump_int
    dispatch[long] = dump_int
