import posixpath
from munch import Munch


class Package(Munch):

    @property
    def url(self):
        """
        Return a kojiweb URL for this resource.

        :returns: ``str``, kojiweb URL like
                  "http://cbs.centos.org/koji/packageinfo?packageID=3726"
        """
        endpoint = 'packageinfo?packageID=%d' % self.id
        return posixpath.join(self.connection.weburl, endpoint)
