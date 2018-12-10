from datetime import datetime, timedelta
import os.path
import posixpath
from munch import Munch, unmunchify
from twisted.internet import defer
from txkoji import task_states
from txkoji.channel import Channel
from txkoji.estimates import average_build_duration
try:
    from urllib.parse import urlparse
    import xmlrpc
except ImportError:
    from urlparse import urlparse
    import xmlrpclib as xmlrpc


# The default kojid sleeptime upstream is 15. The RH builders have this dialed
# up to 45. We'll pick the higher number for estimation purposes.
SLEEPTIME = timedelta(seconds=45)

# A lot of the .params parsing here is conceptually similar to Koji's
# _do_parseTaskParams in the CLI.


class Task(Munch):

    @property
    def arch(self):
        """
        Return an architecture for this task.

        :returns: an arch string (eg "noarch", or "ppc64le"), or None this task
                  has no architecture associated with it.
        """
        if self.method in ('buildArch', 'createdistrepo', 'livecd'):
            return self.params[2]
        if self.method in ('createrepo', 'runroot'):
            return self.params[1]
        if self.method == 'createImage':
            return self.params[3]
        if self.method == 'indirectionimage':
            return self.params[0]['arch']

    @property
    def arches(self):
        """
        Return a list of architectures for this task.

        :returns: a list of arch strings (eg ["ppc64le", "x86_64"]). The list
                  is empty if this task has no arches associated with it.
        """
        if self.method == 'image':
            return self.params[2]
        if self.arch:
            return [self.arch]
        return []

    @property
    def build_id(self):
        """
        Find a build ID for this task.

        Pass this build ID into connection.getBuild() to get the Build class
        for this task.

        This only works for the tagBuild tasks. Alternatively, you can also
        locate the builds for other types of tasks using the listBuilds RPC
        with the taskID kwarg, like listBuilds(taskID=...)

        :returns: a build ID int, or None if no build is associated with this
                  task.
        """
        if self.method == 'tagBuild':
            return self.params[1]

    @property
    def channel(self):
        """
        Return the Channel for this task.

        :returns: an instance of the Channel class.
        """
        return Channel({'id': self.channel_id, 'connection': self.connection})

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
    def created(self):
        """
        Return a parsed created datetime for a task.

        :returns: a datetime object for the time this task was created
        """
        return datetime.utcfromtimestamp(self.create_ts)

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
    def state_name(self):
        """
        Return a human-readable name of this task's state.

        :returns: eg. "OPEN"
        """
        return task_states.to_str(self.state)

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
                  estimated, or the actual datetime, or None if we could not
                  estimate a time for this task method.
        """
        if self.completion_ts:
            # Task is already complete. Return the exact completion time:
            defer.returnValue(self.completed)
        # Get the timestamps from the descendent task that's doing the work:
        if self.method == 'build' or self.method == 'image':
            subtask_completion = yield self.estimate_descendents()
            defer.returnValue(subtask_completion)
        if self.state == task_states.FREE:
            est_completion = yield self._estimate_free()
            defer.returnValue(est_completion)
        avg_delta = yield self.estimate_duration()
        if avg_delta is None:
            defer.returnValue(None)
        est_completion = self.started + avg_delta
        defer.returnValue(est_completion)

    def estimate_duration(self):
        """
        Estimate duration (timedelta) for this task.

        Estimate the average length of time we expect between this task's
        start and end times.

        :returns: deferred that when fired returns a timedelta object for the
                  estimated timedelta, or the actual timedelta, or None if we
                  could not estimate a time for this task method.
        """
        if self.completion_ts:
            # Task is already complete. Return the exact duration timedelta.
            return defer.succeed(self.duration)
        if not self.package:
            # TODO: estimate duration some other way besides
            # getAverageBuildDuration. For example, we could estimate
            # completion time for newRepo/createrepo tasks by looking back at
            # the the past couple of tasks for this tag.
            return defer.succeed(None)
        if self.method == 'tagBuild':
            # These are pretty short. Haphazardly guess the max SLEEPTIME plus
            # a few seconds.
            tag_build_time = SLEEPTIME + timedelta(seconds=15)
            return defer.succeed(tag_build_time)
        return average_build_duration(self.connection, self.package)

    @defer.inlineCallbacks
    def _estimate_free(self):
        """
        Estimate completion time for a free task.

        :returns: deferred that when fired returns a datetime object for the
                  estimated, or the actual datetime, or None if we could not
                  estimate a time for this task method.
        """
        # Query the information we need for this task's channel and package.
        capacity_deferred = self.channel.total_capacity()
        open_tasks_deferred = self.channel.tasks(state=[task_states.OPEN])
        avg_delta_deferred = self.estimate_duration()
        deferreds = [capacity_deferred,
                     open_tasks_deferred,
                     avg_delta_deferred]
        results = yield defer.gatherResults(deferreds, consumeErrors=True)
        capacity, open_tasks, avg_delta = results
        # Ensure this task's channel has spare capacity for this task.
        open_weight = sum([task.weight for task in open_tasks])
        if open_weight >= capacity:
            # TODO: Evaluate all tasks in the channel and
            # determine when enough OPEN tasks will complete so that we can
            # get to OPEN.
            raise NotImplementedError('channel %d is at capacity' %
                                      self.channel_id)
        # A builder will pick up this task and start it within SLEEPTIME.
        # start_time is the maximum amount of time we expect to wait here.
        start_time = self.created + SLEEPTIME
        if avg_delta is None:
            defer.returnValue(None)
        est_completion = start_time + avg_delta
        defer.returnValue(est_completion)

    @defer.inlineCallbacks
    def estimate_descendents(self):
        """
        Estimate from the descendent (child) tasks.

        :returns: deferred that when fired returns a datetime object for the
                  estimated, or actual datetime, or None if there is no support
                  for this task method. Currently the only supported methods
                  here are "build" and "image".
        :raises NoDescendentsError: If we expected to find descendents for this
                  task, but there are none open. Possible explanations:
                  * Koji has not assigned this task to a worker, because it's
                    over capacity, or because it takes a few seconds to assign.
                    You may see descendant tasks in FREE state here, instead of
                    OPEN state.
                  * The makeSRPMFromSCM descendent task for this build task is
                    not yet complete.
                  * The tagBuild descendent task for this build task is not yet
                    complete.
                  If you hit this NoDescendentsError, you may want to try again
                  in a few minutes.
        """
        child_method = None
        if self.method == 'build':
            child_method = 'buildArch'
        if self.method == 'image':
            child_method = 'createImage'
        if child_method is None:
            defer.returnValue(None)
        # Find the open child task and estimate that.
        subtasks = yield self.descendents(method=child_method,
                                          state=task_states.OPEN)
        if not subtasks:
            raise NoDescendentsError('no running %s for task %d' %
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
        if self.method == 'buildNotification':
            return self.params[1]['name']
        if self.method in ('createImage', 'image', 'livecd'):
            return self.params[0]
        if self.method == 'indirectionimage':
            return self.params[0]['name']
        # params[0] is the source URL for these tasks:
        if self.method not in ('build', 'buildArch', 'buildContainer',
                               'buildMaven', 'buildSRPMFromSCM', 'maven'):
            return None
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
                package = package[:-4]
            if self.method == 'buildContainer':
                package += '-container'
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
            return unmunchify(self.request)
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
    def tag(self):
        """
        Return the tag's name (or id number) for this task.

        :returns: An int (tag id) or string (tag name, eg "foo-build").
                  This seems to depend on the task method. For example,
                  buildArch, tagBuild, and tagNotification tasks always return
                  a tag ID here.
                  If you do get an int back here, you'll have to make a
                  separate getTag RPC to get the tag's name.
        """
        if self.method == 'buildArch':
            # Note: buildArch tag will be an int here.
            return self.params[1]
        if self.method in ('createdistrepo', 'distRepo', 'newRepo', 'runroot',
                           'tagBuild', 'waitrepo'):
            return self.params[0]
        if self.method == 'tagNotification':
            return self.params[2]
        if self.method == 'buildMaven':
            return self.params[1]['name']

    @property
    def target(self):
        if self.method in ('build', 'buildContainer', 'chainmaven', 'maven'):
            return self.params[1]
        if self.method == 'buildNotification':
            if self.params[2]:
                return self.params[2]['name']
        if self.method == 'createImage':
            return self.params[4]['name']
        if self.method in ('image', 'livecd'):
            return self.params[3]
        if self.method == 'indirectionimage':
            return self.params[0]['target']
        if self.method == 'wrapperRPM':
            return self.params[1]['name']

    @property
    def url(self):
        """
        Return a kojiweb URL for this resource.

        :returns: ``str``, kojiweb URL like
                  "http://cbs.centos.org/koji/taskinfo?taskID=381617"
        """
        endpoint = 'taskinfo?taskID=%d' % self.id
        return posixpath.join(self.connection.weburl, endpoint)


class NoDescendentsError(Exception):
    """ Could not find open buildArch descendents for this task. """
    pass
