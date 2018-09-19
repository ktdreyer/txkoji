from datetime import timedelta
from glob import glob
import os
from munch import munchify
import treq
import treq_kerberos
from twisted.web.xmlrpc import Proxy
from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet.ssl import PrivateCertificate
from twisted.web.client import Agent
from twisted.web.client import ResponseFailed
from txkoji.ssl import ClientCertPolicy, RootCATrustRoot
try:
    from configparser import SafeConfigParser
    from urllib.parse import urlencode, urlparse, parse_qs
    import xmlrpc
except ImportError:
    from ConfigParser import SafeConfigParser
    from urllib import urlencode
    from urlparse import urlparse, parse_qs
    import xmlrpclib as xmlrpc
from txkoji.query_factory import KojiQueryFactory
from txkoji.cache import Cache
from txkoji.call import Call
from txkoji.task import Task
from txkoji.build import Build
from txkoji.package import Package
from txkoji.exceptions import KojiException, KojiLoginException


__version__ = '0.5.0'


PROFILES = '/etc/koji.conf.d/*.conf'


class Connection(object):

    def __init__(self, profile):
        self.profile = profile
        self.url = self.lookup(profile, 'server')
        self.weburl = self.lookup(profile, 'weburl')
        if not self.url:
            msg = 'no server configured at %s for %s' % (PROFILES, profile)
            raise ValueError(msg)
        self.proxy = Proxy(self.url.encode(), allowNone=True)
        self.proxy.queryFactory = KojiQueryFactory
        self.cache = Cache(self)
        # We populate these on login:
        self.session_id = None
        self.session_key = None
        self.callnum = None

    def lookup(self, profile, setting):
        """ Check koji.conf.d files for this profile's setting.

        :param setting: ``str`` like "server" (for kojihub) or "weburl"
        :returns: ``str``, value for this setting
        """
        for path in glob(PROFILES):
            cfg = SafeConfigParser()
            cfg.read(path)
            if profile not in cfg.sections():
                continue
            if not cfg.has_option(profile, setting):
                continue
            return cfg.get(profile, setting)

    @classmethod
    def connect_from_web(klass, url):
        """
        Find a connection that matches this kojiweb URL.

        Check all koji.conf.d files' kojiweb URLs and load the profile that
        matches the url we pass in here.

        For example, if a user pastes a kojiweb URL into chat, we want to
        discover the corresponding Koji instance hub automatically.

        See also from_web().

        :param url: ``str``, for example
                    "http://cbs.centos.org/koji/buildinfo?buildID=21155"
        :returns: A "Connection" instance
        """
        for path in glob(PROFILES):
            cfg = SafeConfigParser()
            cfg.read(path)
            for profile in cfg.sections():
                if not cfg.has_option(profile, 'weburl'):
                    continue
                weburl = cfg.get(profile, 'weburl')
                if weburl in url:
                    return klass(profile)

    @defer.inlineCallbacks
    def from_web(self, url):
        """
        Reverse-engineer a kojiweb URL into an equivalent API response.

        Only a few kojiweb URL endpoints work here.

        See also connect_from_web().

        :param url: ``str``, for example
                    "http://cbs.centos.org/koji/buildinfo?buildID=21155"
        :returns: deferred that when fired returns a Munch (dict-like) object
                  with data about this resource, or None if we could not parse
                  the url.
        """
        o = urlparse(url)
        endpoint = os.path.basename(o.path)
        if o.query:
            query = parse_qs(o.query)
        result = None
        # Known Kojiweb endpoints:
        endpoints = {
            'buildinfo': ('buildID', self.getBuild),
            'channelinfo': ('channelID', self.getChannel),
            'hostinfo': ('hostID', self.getHost),
            'packageinfo': ('packageID', self.getPackage),
            'taskinfo': ('taskID', self.getTaskInfo),
            'taginfo': ('tagID', self.getTag),
            'targetinfo': ('targetID', self.getTarget),
            'userinfo': ('userID', self.getUser),
        }
        try:
            (param, method) = endpoints[endpoint]
            id_ = int(query[param][0])
            result = yield method(id_)
        except KeyError:
            pass
        defer.returnValue(result)

    def call(self, method, *args, **kwargs):
        """
        Make an XML-RPC call to the server.

        If this client is logged in (with login()), this call will be
        authenticated.

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
        if self.session_id:
            self.proxy.path = self._authenticated_path()
        d = self.proxy.callRemote(method, *args)
        d.addCallback(self._munchify_callback)
        d.addErrback(self._parse_errback)
        if self.callnum is not None:
            self.callnum += 1
        return d

    def _authenticated_path(self):
        """
        Get the path of our XML-RPC endpoint with session auth params added.

        For example:
          /kojihub?session-id=123456&session-key=1234-asdf&callnum=0

        If we're making an authenticated request, we must add these session
        parameters to the hub's XML-RPC endpoint.

        :return: a path suitable for twisted.web.xmlrpc.Proxy
        """
        basepath = self.proxy.path.decode().split('?')[0]
        params = urlencode({'session-id': self.session_id,
                            'session-key': self.session_key,
                            'callnum': self.callnum})
        result = '%s?%s' % (basepath, params)
        return result.encode('utf-8')

    def __getattr__(self, name):
        return Call(self, name)

    @defer.inlineCallbacks
    def getAverageBuildDuration(self, package, **kwargs):
        """
        Return a timedelta that Koji considers to be average for this package.

        Calls "getAverageBuildDuration" XML-RPC.

        :param package: ``str``, for example "ceph"
        :returns: deferred that when fired returns a datetime object for the
                  estimated duration, or None if we could find no estimate for
                  this package.
        """
        seconds = yield self.call('getAverageBuildDuration', package, **kwargs)
        if seconds is None:
            defer.returnValue(None)
        defer.returnValue(timedelta(seconds=seconds))

    @defer.inlineCallbacks
    def getBuild(self, build_id, **kwargs):
        """
        Load all information about a build and return a custom Build class.

        Calls "getBuild" XML-RPC.

        :param build_id: ``int``, for example 12345
        :returns: deferred that when fired returns a Build (Munch, dict-like)
                  object representing this Koji build, or None if no build was
                  found.
        """
        buildinfo = yield self.call('getBuild', build_id, **kwargs)
        build = Build.fromDict(buildinfo)
        if build:
            build.connection = self
        defer.returnValue(build)

    @defer.inlineCallbacks
    def getPackage(self, name, **kwargs):
        """
        Load information about a package and return a custom Package class.

        Calls "getPackage" XML-RPC.

        :param package_id: ``int``, for example 12345
        :returns: deferred that when fired returns a Package (Munch, dict-like)
                  object representing this Koji package, or None if no build
                  was found.
        """
        packageinfo = yield self.call('getPackage', name, **kwargs)
        package = Package.fromDict(packageinfo)
        if package:
            package.connection = self
        defer.returnValue(package)

    @defer.inlineCallbacks
    def getTaskDescendents(self, task_id, **kwargs):
        """
        Load all information about a task's descendents into Task classes.

        Calls "getTaskDescendents" XML-RPC (with request=True to get the full
        information.)

        :param task_id: ``int``, for example 12345, parent task ID
        :returns: deferred that when fired returns a list of Task (Munch,
                  dict-like) objects representing Koji tasks.
        """
        kwargs['request'] = True
        data = yield self.call('getTaskDescendents', task_id, **kwargs)
        tasks = []
        for tdata in data[str(task_id)]:
            task = Task.fromDict(tdata)
            task.connection = self
            tasks.append(task)
        defer.returnValue(tasks)

    @defer.inlineCallbacks
    def getTaskInfo(self, task_id, **kwargs):
        """
        Load all information about a task and return a custom Task class.

        Calls "getTaskInfo" XML-RPC (with request=True to get the full
        information.)

        :param task_id: ``int``, for example 12345
        :returns: deferred that when fired returns a Task (Munch, dict-like)
                  object representing this Koji task, or none if no task was
                  found.
        """
        kwargs['request'] = True
        taskinfo = yield self.call('getTaskInfo', task_id, **kwargs)
        task = Task.fromDict(taskinfo)
        if task:
            task.connection = self
        defer.returnValue(task)

    @defer.inlineCallbacks
    def listBuilds(self, package, **kwargs):
        """
        Get information about all builds of a package.

        Calls "listBuilds" XML-RPC, with an enhancement: you can also pass a
        string here for the package name instead of the package ID number.

        :param package: ``int`` (packageID) or ``str`` (package name).
        :returns: deferred that when fired returns a list of Build objects
                  for this package.
        """
        if isinstance(package, int):
            package_id = package
        else:
            package_data = yield self.getPackage(package)
            if package_data is None:
                defer.returnValue([])
            package_id = package_data.id
        data = yield self.call('listBuilds', package_id, **kwargs)
        builds = []
        for bdata in data:
            build = Build.fromDict(bdata)
            build.connection = self
            builds.append(build)
        defer.returnValue(builds)

    @defer.inlineCallbacks
    def listTasks(self, opts={}, queryOpts={}):
        """
        Get information about all Koji tasks.

        Calls "listTasks" XML-RPC.

        :param opts: ``dict``. Eg. {'state': [task_states.OPEN]}
        :param queryOpts: ``dict``. Eg. {'order' : 'priority,create_time'}
        :returns: deferred that when fired returns a list of Task objects.
        """
        opts['decode'] = True  # decode xmlrpc data in "request"
        data = yield self.call('listTasks', opts, queryOpts)
        tasks = []
        for tdata in data:
            task = Task.fromDict(tdata)
            task.connection = self
            tasks.append(task)
        defer.returnValue(tasks)

    @defer.inlineCallbacks
    def login(self):
        """
        Return True if we successfully logged into this Koji hub.

        We support GSSAPI and SSL Client authentication (not the old-style
        krb-over-xmlrpc krbLogin method).

        :returns: deferred that when fired returns True
        """
        authtype = self.lookup(self.profile, 'authtype')
        if authtype is None:
            cert = self.lookup(self.profile, 'cert')
            if cert and os.path.isfile(os.path.expanduser(cert)):
                authtype = 'ssl'
            # Note: official koji cli is a little more lax here. If authtype is
            # None and we have a valid kerberos ccache, we still try kerberos
            # auth.
        if authtype == 'kerberos':
            # Note: we don't try the old-style kerberos login here.
            result = yield self._gssapi_login()
        elif authtype == 'ssl':
            result = yield self._ssl_login()
        else:
            raise NotImplementedError('unsupported auth: %s' % authtype)
        self.session_id = result['session-id']
        self.session_key = result['session-key']
        self.callnum = 0  # increment this on every call for this session.
        defer.returnValue(True)

    def _gssapi_login(self):
        """
        Authenticate to the /ssllogin endpoint with GSSAPI authentication.

        :returns: deferred that when fired returns a dict from sslLogin
        """
        method = treq_kerberos.post
        auth = treq_kerberos.TreqKerberosAuth(force_preemptive=True)
        return self._request_login(method, auth=auth)

    def _ssl_agent(self):
        """
        Get a Twisted Agent that performs Client SSL authentication for Koji.
        """
        # Load "cert" into a PrivateCertificate.
        certfile = self.lookup(self.profile, 'cert')
        certfile = os.path.expanduser(certfile)
        with open(certfile) as certfp:
            pemdata = certfp.read()
            client_cert = PrivateCertificate.loadPEM(pemdata)

        trustRoot = None  # Use Twisted's platformTrust().
        # Optionally load "serverca" into a Certificate.
        servercafile = self.lookup(self.profile, 'serverca')
        if servercafile:
            servercafile = os.path.expanduser(servercafile)
            trustRoot = RootCATrustRoot(servercafile)

        policy = ClientCertPolicy(trustRoot=trustRoot, client_cert=client_cert)
        return Agent(reactor, policy)

    def _ssl_login(self):
        """
        Authenticate to the /ssllogin endpoint with Client SSL authentication.

        :returns: deferred that when fired returns a dict from sslLogin
        """
        method = treq.post
        agent = self._ssl_agent()
        return self._request_login(method, agent=agent)

    @defer.inlineCallbacks
    def _request_login(self, method, **kwargs):
        """
        Send a treq HTTP POST request to /ssllogin

        :param method: treq method to use, for example "treq.post" or
                       "treq_kerberos.post".
        :param kwargs: kwargs to pass to treq or treq_kerberos, for example
                       "auth" or "agent".

        :returns: deferred that when fired returns a dict from sslLogin
        """
        url = self.url + '/ssllogin'
        # Build the XML-RPC HTTP request body by hand and send it with
        # treq.
        factory = KojiQueryFactory(path=None, host=None, method='sslLogin')
        payload = factory.payload
        try:
            response = yield method(url, data=payload, **kwargs)
        except ResponseFailed as e:
            failure = e.reasons[0]
            failure.raiseException()
        if response.code > 200:
            raise KojiLoginException('HTTP %d error' % response.code)
        # Process the XML-RPC response content from treq.
        content = yield response.content()
        if hasattr(xmlrpc, 'loads'):  # Python 2:
            result = xmlrpc.loads(content)[0][0]
        else:
            result = xmlrpc.client.loads(content)[0][0]
        defer.returnValue(result)

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
        if hasattr(xmlrpc, 'Fault'):  # Python 2:
            fault = xmlrpc.Fault
        else:
            fault = xmlrpc.client.Fault
        if isinstance(error.value, fault):
            # TODO: specific errors here, see koji/__init__.py
            if error.value.faultCode >= 1000 and error.value.faultCode <= 1022:
                raise KojiException(error.value.faultString)
            raise KojiException(error.value)
        # We don't know what this is, so just raise it.
        raise error
