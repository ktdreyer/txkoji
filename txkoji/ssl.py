import os
from twisted.internet.ssl import platformTrust
from twisted.internet.ssl import optionsForClientTLS
from twisted.internet._sslverify import IOpenSSLTrustRoot
from twisted.web.client import BrowserLikePolicyForHTTPS
from zope.interface import implementer

"""
This module provides some helper classes for working with Client SSL
authentication and Twisted.
"""


def trustRoot(serverca=None):
    """
    Return a trustRoot object for this connection.

    :param str serverca: Path to a PEM-formatted CA certificate to trust.
                         If the user does not specify a serverca, the default
                         behavior is to return the system-wide CA bundle
                         with platformTrust().
    :returns: This return value is intended as the trustRoot argument to
              ClientCertPolicy() or optionsForClientTLS().
    """
    if serverca:
        servercafile = os.path.expanduser(serverca)
        return RootCATrustRoot(servercafile)
    return platformTrust()


class ClientCertPolicy(BrowserLikePolicyForHTTPS):
    """ SSL client policy that does client authentication. """
    def __init__(self, trustRoot, client_cert):
        self.client_cert = client_cert
        super(ClientCertPolicy, self).__init__(trustRoot)

    def creatorForNetloc(self, hostname, port):
        return optionsForClientTLS(hostname=hostname.decode("ascii"),
                                   clientCertificate=self.client_cert)


@implementer(IOpenSSLTrustRoot)
class RootCATrustRoot(object):
    """
    This class trusts one particular CA bundle file in the SSL context.

    (See OpenSSLDefaultPaths for an alternate example, where it loads all the
    OpenSSL default verify paths instead.)

    Pass an instance of this class as the trustRoot argument to
    BrowserLikePolicyForHTTPS (or ClientCertPolicy).
    """
    def __init__(self, root_certificate_path):
        self.root_certificate_path = root_certificate_path

    def _addCACertsToContext(self, context):
        context.load_verify_locations(self.root_certificate_path)
