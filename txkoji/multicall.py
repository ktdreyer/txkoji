from datetime import timedelta
from munch import Munch
from txkoji.call import Call
from txkoji.exceptions import KojiException
from txkoji.build import Build
from txkoji.channel import Channel
from txkoji.task import Task
from txkoji.package import Package
try:
    from xmlrpc.client import MultiCallIterator
except ImportError:
    # Python 2
    from xmlrpclib import MultiCallIterator


class MultiCall(object):
    """
    Callable abstract class representing a series of Koji RPCs.

    :param connection: ``txkoji.Connection``
    """
    def __init__(self, connection):
        self.connection = connection
        self.calls = []

    def __getattr__(self, name):
        return Call(self, name)

    def __call__(self):
        """
        Send the all our individual calls to the the server as a single
        "system.multicall" RPC.

        Resets the list of stored calls.
        :returns: deferred that when fired returns an iterator for results,
                  one for each call. The results will either be Munch objects,
                  or else raise exceptions.
        """
        d = self.connection.call('system.multicall', self.calls)
        d.addCallback(self._multicall_callback, self.calls)
        self.calls = []
        return d

    def call(self, name, *args, **kwargs):
        """
        Add a new call to the list that we will submit to the server.

        Similar to txkoji.Connection.call(), but this will store the call
        for later instead of sending it now.
        """
        # Like txkoji.Connection, we always want the full request for tasks:
        if name in ('getTaskInfo', 'getTaskDescendants'):
            kwargs['request'] = True
        if kwargs:
            kwargs['__starstar'] = True
            args = args + (kwargs,)
        payload = {'methodName': name, 'params': args}
        self.calls.append(payload)

    def _multicall_callback(self, values, calls):
        """
        Fires when we get information back from the XML-RPC server.

        This is processes the raw results of system.multicall into a usable
        iterator of values (and/or Faults).

        :param values: list of data txkoji.Connection.call()
        :param calls: list of calls we sent in this multicall RPC
        :returns: KojiMultiCallIterator with the resulting values from all our
                  calls.
        """
        result = KojiMultiCallIterator(values)
        result.connection = self.connection
        result.calls = calls
        return result


class KojiMultiCallIterator(MultiCallIterator):
    """
    An XML-RPC MultiCall iterator with some extra features for txkoji.

    The differences from stdlib version:
    1. Handle Munch data types, since txkoji.Connection.call() returns these.
    2. Inject the txkoji.Connection into each Munch value we return.
    2. Raise KojiExceptions for all XML-RPC faults.
    """
    def __getitem__(self, i):
        result = self.results[i]
        call = self.calls[i]
        # If it's a list, then this particular call succeeded. Return the
        # result.
        if isinstance(result, list):
            method_name = call['methodName']
            value = result[0]
            return self.rich_item(method_name, value)
        # If it's not a list, it must be a fault.
        fault_string = result['faultString']
        # We know Koji's functioning here enough to return a response, so
        # raise a nice KojiException instead of the xmlrpc.client.Fault:
        raise KojiException(fault_string)

    # TODO: need to generalize this rich item converstion logic so we use the
    # same logic in txkoji.Connection for single RPCs.
    def rich_item(self, method_name, value):
        """
        Convert this value into the rich txkoji objects (if applicable)
        """
        if value is None:
            return None
        if method_name == 'getAverageBuildDuration':
            return timedelta(seconds=value)
        types = (Build, Channel, Package, Task)
        if isinstance(value, Munch):
            for type_ in types:
                if type_.__name__ in method_name:
                    item = type_(value)
                    item.connection = self.connection
                    return item
        if isinstance(value, list):
            # Do this same rich item conversion for list of Munch objects
            items_list = [self.rich_item(method_name, val) for val in value]
            return items_list
        return value
