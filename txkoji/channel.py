from munch import Munch
from twisted.internet import defer


class Channel(Munch):

    def hosts(self, **kwargs):
        """
        Convenience wrapper around listHosts(...) for this channel ID.

        :param **kwargs: keyword arguments to the listHosts RPC.
        :returns: deferred that when fired returns a list of hosts (dicts).
        """
        kwargs['channelID'] = self.id
        return self.connection.listHosts(**kwargs)

    def tasks(self, **opts):
        """
        Convenience wrapper around listTasks(...) for this channel ID.

        Tasks are sorted by priority and creation time.

        :param **opts: "opts" dict to the listTasks RPC.
                       For example, "state=[task_states.OPEN]" will return
                       only the "OPEN" tasks.
        :returns: deferred that when fired returns a list of Tasks.
        """
        opts['channel_id'] = self.id
        qopts = {'order': 'priority,create_time'}
        return self.connection.listTasks(opts, qopts)

    @defer.inlineCallbacks
    def total_capacity(self):
        """
        Find the total task capacity available for this channel.

        Query all the enabled hosts for this channel and sum up all the
        capacities.

        Each task has a "weight". Each task will be in "FREE" state until
        there is enough capacity for the task's "weight" on a host.

        :returns: deferred that when fired returns a float value: the total
                  task weight that this channel can have open simultaneously.
        """
        # Ensure this task's channel has spare capacity for this task.
        total_capacity = 0
        hosts = yield self.hosts(enabled=True)
        for host in hosts:
            total_capacity += host.capacity
        defer.returnValue(total_capacity)
