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

    def tags(self):
        """
        Find the tags for this build.

        Convenience wrapper around the listTags RPC.

        :returns: deferred that when fired returns a (possibly empty) list of
                  Munch (dict-like) objects representing each tag for this
                  build.
        """
        return self.connection.listTags(self.id)

    @defer.inlineCallbacks
    def target(self):
        """
        Find the target name for this build.

        :returns: deferred that when fired returns the build task's target
                  name. If we could not determine the build task, or the task's
                  target, return None.
        """
        task = yield self.task()
        if not task:
            yield defer.succeed(None)
            defer.returnValue(None)
        defer.returnValue(task.target)

    def task(self):
        """
        Find the task for this build.

        Wraps the getTaskInfo RPC.

        :returns: deferred that when fired returns the Task object, or None if
                  we could not determine the task for this build.
        """
        # If we have no .task_id, this is a no-op to return None.
        if not self.task_id:
            return defer.succeed(None)
        return self.connection.getTaskInfo(self.task_id)

    @property
    def task_id(self):
        """
        Hack to return a task ID for a build, including container CG builds.

        We have something for this in Brewweb, but not yet for upstream Koji:
        https://pagure.io/koji/issue/215
        """
        if self['task_id']:
            return self['task_id']
        if self.extra and 'container_koji_task_id' in self.extra:
            return self.extra['container_koji_task_id']
