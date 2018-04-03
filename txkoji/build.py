from datetime import datetime, timedelta
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

    @defer.inlineCallbacks
    def estimate_completion(self):
        """
        Estimate completion time for a build.

        :returns: deferred that when fired returns a datetime object for the
                  estimated or actual datetime.
        """
        if self.state != build_states.BUILDING:
            # Build is already complete. Return the exact completion time:
            defer.returnValue(self.completed)
        avg_delta = yield self.connection.getAverageBuildDuration(self.name)
        est_completion = self.started + avg_delta
        defer.returnValue(est_completion)
