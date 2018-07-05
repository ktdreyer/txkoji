from twisted.internet.ssl import optionsForClientTLS
from twisted.internet._sslverify import IOpenSSLTrustRoot
from twisted.web.client import BrowserLikePolicyForHTTPS
from zope.interface import implementer

"""
This module provides some helper classes for working with Client SSL
authentication and Twisted.

There is no simple way to trust an SSL certificate bundle with Twisted. Twisted
exposes "trustRoot" that expects a trustRootFromCertificates (list of
Certificate objects), but Certificate.loadPEM() can only load a single PEM file
at a time. This means we cannot do something simple like
Certificate.loadPEM('/etc/pki/tls/certs/ca-bundle.trust.crt').

https://stackoverflow.com/questions/26166444/twisted-python-how-to-create-a-twisted-web-client-browserlikepolicyforhttps-with

The solution is to implement our own RootCATrustRoot trustRoot class that
points at a single SSL root bundle.

Warning: this uses several private Twisted interfaces, (_sslverify and
IOpenSSLTrustRoot), so this might break with future Twisted releases.

If this ends up being too fragile, we could just take this out and require
users to trust their custom Koji CAs system-wide. Alternatively, OpenSSL will
load a custom CA from the SSL_CERT_FILE environmnet variable.
"""


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
