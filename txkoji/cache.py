import errno
import os
from twisted.internet import defer


class Cache(object):
    def __init__(self, connection, directory=None):
        """
        Read-through cache manager for user and tag names.

        This cache will write everything into XDG_CACHE_HOME, or ~/.cache.

        This class does no eviction or expiration - all the data will persist
        in the cache forever. If you want to clear the cache, you'll need to
        delete files manually for now.

        :param connection: txkoji.Connection
        :param directory: optional, directory on disk to store cache data.
        """
        self.connection = connection
        self.directory = directory
        if self.directory is None:
            xdg_cache_home = os.getenv('XDG_CACHE_HOME')
            if xdg_cache_home:
                self.directory = os.path.join(xdg_cache_home, 'txkoji')
            else:
                self.directory = os.path.expanduser('~/.cache/txkoji')

    def get_name(self, type_, id_):
        """
        Read a cached name if available.

        :param type_: str, "owner" or "tag"
        :param id_: int, eg. 123456
        :returns: str, or None
        """
        cachefile = self.filename(type_, id_)
        try:
            with open(cachefile, 'r') as f:
                return f.read()
        except (OSError, IOError) as e:
            if e.errno != errno.ENOENT:
                raise

    def put_name(self, type_, id_, name):
        """
        Write a cached name to disk.

        :param type_: str, "user" or "tag"
        :param id_: int, eg. 123456
        :returns: None
        """
        cachefile = self.filename(type_, id_)
        dirname = os.path.dirname(cachefile)
        try:
            os.makedirs(dirname)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        with open(cachefile, 'w') as f:
            f.write(name)

    def filename(self, type_, id_):
        """
        cache filename to read for this type/id.

        :param type_: str, "user" or "tag"
        :param id_: int, eg. 123456
        :returns: str
        """
        profile = self.connection.profile
        return os.path.join(self.directory, profile, type_, str(id_))

    @defer.inlineCallbacks
    def get_or_load_name(self, type_, id_, method):
        """
        read-through cache for a type of object's name.

        If we don't have a cached name for this type/id, then we will query the
        live Koji server and store the value before returning.

        :param type_: str, "user" or "tag"
        :param id_: int, eg. 123456
        :param method: function to call if this value is not in the cache.
                       This method must return a deferred that fires with an
                       object with a ".name" attribute.
        :returns: deferred that when fired returns a str, or None
        """
        name = self.get_name(type_, id_)
        if name is not None:
            defer.returnValue(name)
        instance = yield method(id_)
        if instance is None:
            defer.returnValue(None)
        self.put_name(type_, id_, instance.name)
        defer.returnValue(instance.name)

    def user_name(self, id_):
        """
        read-through cache for a user name.

        :param id_: int, eg. 123456
        :returns: deferred that when fired returns a str, or None
        """
        return self.get_or_load_name('user', id_, self.connection.getUser)

    def tag_name(self, id_):
        """
        read-through cache for a tag name.

        :param id_: int, eg. 123456
        :returns: deferred that when fired returns a str, or None
        """
        return self.get_or_load_name('tag', id_, self.connection.getTag)
