from datetime import datetime
import os.path
import posixpath
from munch import Munch
from twisted.internet import defer
from txkoji import task_states
try:
    from urllib.parse import urlparse
    import xmlrpc
except ImportError:
    from urlparse import urlparse
    import xmlrpclib as xmlrpc


class Task(Munch):

    @property
    def completed(self):
        """
        Return a parsed completion datetime for a task.

        :returns: a datetime object for the time this task finished,
                  or None if the task is not completed.
        """
        if not self.completion_ts:
            return None
        return datetime.utcfromtimestamp(self.completion_ts)

    @property
    def started(self):
        """
        Return a parsed started datetime for a task.

        :returns: a datetime object for the time this task started
        """
        if not self.start_ts:
            return None
        return datetime.utcfromtimestamp(self.start_ts)

    @property
    def duration(self):
        """
        Return a timedelta for this task.

        Measure the time between this task's start and end time, or "now"
        if the task has not yet finished.

        :returns: timedelta object, or None if the task has not even started.
        """
        if not self.started:
            return None
        start = self.started
        end = self.completed
        if not end:
            end = datetime.utcnow()
        return end - start

    @defer.inlineCallbacks
    def estimate_completion(self):
        """
        Estimate completion time for a task.

        :returns: deferred that when fired returns a datetime object for the
                  estimated or actual datetime.
        """
        if self.completion_ts:
            # Task is already complete. Return the exact completion time:
            defer.returnValue(self.completed)
        # Get the timestamps from the descendent task that's doing the work:
        if self.method == 'build' or self.method == 'image':
            subtask_completion = yield self.estimate_descendents()
            defer.returnValue(subtask_completion)
        if not self.start_ts:
            raise ValueError('no start time, task in %s state' % self.state)
        package = self.package
        avg_delta = yield self.connection.getAverageBuildDuration(package)
        est_completion = self.started + avg_delta
        defer.returnValue(est_completion)

    @defer.inlineCallbacks
    def estimate_descendents(self):
        """
        Estimate from the descendent (child) tasks.

        :returns: deferred that when fired returns a datetime object for the
                  estimated or actual datetime.
        """
        if self.method == 'build':
            child_method = 'buildArch'
        if self.method == 'image':
            child_method = 'createImage'
        # Find the open child task and estimate that.
        subtasks = yield self.descendents(method=child_method,
                                          state=task_states.OPEN)
        if not subtasks:
            # Maybe koji has not assigned this task to a worker (over
            # capacity), or maybe makeSRPMfromSCM is still running.
            # Try again in a few minutes?
            raise ValueError('no running %s for task %d' %
                             (child_method, self.id))
        # Find subtask with the most recent start time:
        build_task = subtasks[0]
        for subtask in subtasks:
            if subtask.start_ts > build_task.start_ts:
                build_task = subtask
        subtask_completion = yield build_task.estimate_completion()
        defer.returnValue(subtask_completion)

    @defer.inlineCallbacks
    def descendents(self, method=None, state=None):
        """
        Find descendant tasks, optionally filtered by method and/or state.

        :param method: (optional) filter for tasks, eg. "buildArch".
        :param state: (optional) filter for tasks, eg. task_states.OPEN.
        :returns: deferred that when fired returns a list of Tasks.
        """
        subtasks = yield self.connection.getTaskDescendents(self.id)
        if method:
            subtasks = [t for t in subtasks if t.method == method]
        if state:
            subtasks = [t for t in subtasks if t.state == state]
        defer.returnValue(subtasks)

    @property
    def package(self):
        """
        Find a package name from a build task's parameters.

        :returns: name of the package this build task is building.
        :raises: ValueError if we could not parse this tasks's request params.
        """
        # (I wish there was a better way to do this.)
        source = self.params[0]
        o = urlparse(source)
        # build tasks can load an SRPM from a "cli-build" tmpdir:
        if source.endswith('.src.rpm'):
            srpm = os.path.basename(source)
            (name, version, release) = srpm.rsplit('-', 2)
            # Note we're throwing away version and release here. They could be
            # useful eventually, maybe in a "Package" class.
            return name
        # or an allowed SCM:
        elif o.scheme:
            package = os.path.basename(o.path)
            if package.endswith('.git'):
                return package[:-4]
            return package
        raise ValueError('could not parse source "%s"' % source)

    @property
    def params(self):
        """
        Return a list of parameters in this task's request.

        If self.request is already a list, simply return it.

        If self.request is a raw XML-RPC string, parse it and return the
        params.
        """
        if isinstance(self.request, list):
            return self.request
        (params, _) = xmlrpc.loads(self.request)
        return params

    @property
    def is_scratch(self):
        for param in self.params:
            if isinstance(param, dict):
                if param.get('scratch'):
                    return True
        return False

    @property
    def url(self):
        """
        Return a kojiweb URL for this resource.

        :returns: ``str``, kojiweb URL like
                  "http://cbs.centos.org/koji/taskinfo?taskID=381617"
        """
        endpoint = 'taskinfo?taskID=%d' % self.id
        return posixpath.join(self.connection.weburl, endpoint)
