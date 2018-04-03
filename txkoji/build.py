import posixpath
from datetime import datetime
from munch import Munch
from twisted.internet import defer
from txkoji import build_states


class Build(Munch):

    @property
    def completed(self):
        """
        Return a parsed completion datetime for a build.

        :returns: a datetime object for the time this build finished,
                  or None if the build is not completed.
        """
        if not self.completion_ts:
            return None
        return datetime.utcfromtimestamp(self.completion_ts)

    @property
    def started(self):
        """
        Return a parsed started datetime for a build.

        :returns: a datetime object for the time this build started
        """
        return datetime.utcfromtimestamp(self.start_ts)

    @property
    def duration(self):
        """
        Return a timedelta for this build.

        Measure the time between this build's start and end time, or "now"
        if the build has not yet finished.

        :returns: timedelta object
        """
        if self.completion_ts:
            end = self.completed
        else:
            end = datetime.utcnow()
        return end - self.started

    @property
    def url(self):
        """
        Return a kojiweb URL for this resource.

        :returns: ``str``, kojiweb URL like
                  "http://cbs.centos.org/koji/buildinfo?buildID=21155"
        """
        endpoint = 'buildinfo?buildID=%d' % self.build_id
        return posixpath.join(self.connection.weburl, endpoint)

    @defer.inlineCallbacks
    def estimate_completion(self):
        """
        Estimate completion time for a build.

        This calls getAverageBuildDuration on the hub for this package. This
        value is a very rough guess, an average for all completed builds in the
        system.

        For now this is better than nothing, but I'm recording a few thoughts
        here for posterity:

        A more advanced implementation of for estimating build times would
        track unique averages per build target. Early releases of Ceph "Hammer"
        versions would build much more quickly than newer Ceph releases like
        "Mimic", and the current method simply averages all of them.

        Also, different Koji build targets can have different arches. When we
        build ceph in "newarch" side tags, those build times are wildly beyond
        the average, but they influence this average too, subtly throwing it
        off for the x86-only builds that I care about.

        :returns: deferred that when fired returns a datetime object for the
                  estimated or actual datetime.
        """
        if self.state != build_states.BUILDING:
            # Build is already complete. Return the exact completion time:
            defer.returnValue(self.completed)
        avg_delta = yield self.connection.getAverageBuildDuration(self.name)
        est_completion = self.started + avg_delta
        defer.returnValue(est_completion)
