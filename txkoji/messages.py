import json
from txkoji.build import Build
from txkoji.task import Task
from twisted.internet import defer
from twisted.python.compat import StringType

"""
A set of "event" classes representing the messages types that Koji publishes.

Features:

* Standardize ingestion of Stompest Frames / JSON bodies with the
  "from_frame()" method. Eventually we could support other Python messaging
  libraries here.

* Normalize the "owner/owner_id/owner_name" stuff to a single "user()"
  method.

* Unified "tag()" method for all TaskStateChange and TagUntag events.
"""

# See Koji's plugins/hub/messagebus.py for the events that Koji announces.


class BuildStateChange(object):
    def __init__(self, build, event):
        self.build = build
        self.event = event  # str, eg "COMPLETE". See txkoji.build_states.

    @classmethod
    def from_frame(klass, frame, connection):
        """
        Create a new BuildStateChange event from a Stompest Frame.
        """
        event = frame.headers['new']
        data = json.loads(frame.body)
        info = data['info']
        build = Build.fromDict(info)
        build.connection = connection
        return klass(build, event)

    @property
    def url(self):
        """ Return a kojiweb URL for this change. """
        return self.build.url

    def user(self):
        """ Return a (deferred) Koji user name for this change. """
        # All BuildStateChange messages *should* have owner_name populated now.
        # See BREW-1640.
        return defer.succeed(self.build.owner_name)


class TaskStateChange(object):
    def __init__(self, task, event):
        self.task = task
        self.event = event  # str, eg "FREE". See txkoji.task_states.

    @classmethod
    def from_frame(klass, frame, connection):
        """
        Create a new TaskStateChange event from a Stompest Frame.
        """
        event = frame.headers['new']
        data = json.loads(frame.body)
        info = data['info']
        task = Task.fromDict(info)
        task.connection = connection
        return klass(task, event)

    def tag(self):
        """ Return a (deferred) cached Koji tag name for this change. """
        name_or_id = self.task.tag
        if name_or_id is None:
            return defer.succeed(None)
        if isinstance(name_or_id, StringType):
            return defer.succeed(name_or_id)
        if isinstance(name_or_id, int):
            return self.task.connection.cache.tag_name(name_or_id)
        return defer.fail()

    @property
    def url(self):
        """ Return a kojiweb URL for this change. """
        return self.task.url

    def user(self):
        """ Return a (deferred) cached Koji user name for this change. """
        # Note, do any tasks really have an "owner_id", or are they all
        # "owner"?
        owner_id = getattr(self.task, 'owner_id', self.task.owner)
        return self.task.connection.cache.user_name(owner_id)


class TagUntag(object):
    """ Tagging or Untagging an existing build. """
    def __init__(self, build, event, tag, user):
        self.build = build
        self.event = event  # str, eg "Tag" or "Untag"
        self.tag = tag  # str, tag name
        self._user = user  # str, user name

    @classmethod
    def from_frame(klass, frame, connection):
        """
        Create a new TagUntag event from a Stompest Frame.
        """
        event = frame.headers['type']  # "Tag" / "Untag"
        tag = frame.headers['tag']
        user = frame.headers['user']
        data = json.loads(frame.body)
        info = data['build']
        build = Build.fromDict(info)
        build.connection = connection
        return klass(build, event, tag, user)

    @property
    def url(self):
        """ Return a kojiweb URL for this change. """
        return self.build.url

    def user(self):
        """ Return a (deferred) Koji user name for this change. """
        return defer.succeed(self._user)
