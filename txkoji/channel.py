from munch import Munch


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
