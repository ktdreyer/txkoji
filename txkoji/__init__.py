from munch import munchify
from glob import glob
from twisted.web.xmlrpc import Proxy
from twisted.internet import defer
try:
    from configparser import SafeConfigParser
    import xmlrpc
except ImportError:
    from ConfigParser import SafeConfigParser
    import xmlrpclib as xmlrpc


__version__ = '0.0.1'


PROFILES = '/etc/koji.conf.d/*.conf'


class Call(object):
    """ Callable abstract class representing a Koji RPC, eg "getTag". """
    def __init__(self, connection, name):
        self.connection = connection
        self.name = name

    def __call__(self, *args, **kwargs):
        return self.connection.call(self.name, *args, **kwargs)


class Connection(object):

    def __init__(self, profile):
        self.url = self.lookup_hub(profile)
        if not self.url:
            msg = 'no server configured at %s for %s' % (PROFILES, profile)
            raise ValueError(msg)
        self.proxy = Proxy(self.url.encode())

    def lookup_hub(self, profile):
        """ Check koji.conf.d files for this profile's Kojihub URL. """
        for path in glob(PROFILES):
            cfg = SafeConfigParser()
            cfg.read(path)
            if profile not in cfg.sections():
                continue
            if not cfg.has_option(profile, 'server'):
                continue
            return cfg.get(profile, 'server')

    def call(self, method, *args, **kwargs):
        """
        Make an XML-RPC call to the server. This method does not auth to the
        server (TODO).

        Koji has its own custom implementation of XML-RPC that supports named
        args (kwargs). For example, to use the "queryOpts" kwarg:

          d = client.call('listBuilds', package_id,
                          queryOpts={'order': 'creation_ts'})

        In this example, the server will order the list of builds according to
        the "creation_ts" database column. Many of Koji's XML-RPC methods have
        optional kwargs that you can set as needed.

        :returns: deferred that when fired returns a dict with data from this
                  XML-RPC call.
        """
        if kwargs:
            kwargs['__starstar'] = True
            args = args + (kwargs,)
        d = self.proxy.callRemote(method, *args)
        d.addCallback(self._munchify_callback)
        d.addErrback(self._parse_errback)
        return d

    def __getattr__(self, name):
        return Call(self, name)

    @defer.inlineCallbacks
    def listBuilds(self, package, **kwargs):
        """
        Get information about all builds of a package.

        Calls "listBuilds" XML-RPC, with an enhancement: you can also pass a
        string here for the package name instead of the package ID number.

        :param package: ``int`` (packageID) or ``str`` (package name).
        :returns: deferred that when fired returns an Munch (dict-like) object
                  representing this package.
        """
        if isinstance(package, int):
            package_id = package
        else:
            package_data = yield self.getPackage(package)
            package_id = package_data.id
        builds = yield self.call('listBuilds', package_id, **kwargs)
        defer.returnValue(builds)

    def _munchify_callback(self, value):
        """
        Fires when we get user information back from the XML-RPC server.

        This is a generic callback for when we do not want to post-process the
        XML-RPC server's data further.

        :param value: dict of data from XML-RPC server.
        :returns: ``Munch`` (dict-like) object
        """
        return munchify(value)

    def _parse_errback(self, error):
        """
        Parse an error from an XML-RPC call.

        raises: ``IOError`` when the Twisted XML-RPC connection times out.
        raises: ``KojiException`` if we got a response from the XML-RPC
                server but it is not one of the ``xmlrpc.Fault``s that
                we know about.
        raises: ``Exception`` if it is not one of the above.
        """
        if isinstance(error.value, IOError):
            raise error.value
        if isinstance(error.value, xmlrpc.Fault):
            # TODO: specific errors here, see koji/__init__.py
            if error.value.faultCode >= 1000 and error.value.faultCode <= 1022:
                raise KojiException(error.value.faultString)
            raise KojiException(error.value)
        # We don't know what this is, so just raise it.
        raise error


class KojiException(Exception):
    pass
