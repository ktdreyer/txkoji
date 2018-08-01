class Call(object):
    """
    Callable abstract class representing a Koji RPC, eg "getTag".

    :param connection: ``txkoji.Connection``
    :param name: XML-RPC method name to call on the server, eg. "getTag".
    """
    def __init__(self, connection, name):
        self.connection = connection
        self.name = name

    def __call__(self, *args, **kwargs):
        return self.connection.call(self.name, *args, **kwargs)
