Async interface to Koji, using Twisted
======================================

.. image:: https://travis-ci.org/ktdreyer/txkoji.svg?branch=master
             :target: https://travis-ci.org/ktdreyer/txkoji

.. image:: https://badge.fury.io/py/txkoji.svg
             :target: https://badge.fury.io/py/txkoji

Access Koji's XML-RPC API asynchronously (non-blocking) using the Twisted
framework.

This supports the GSSAPI or Client SSL login methods.

Simple Example: Fetching a user's name
--------------------------------------

.. code-block:: python

    from txkoji import Connection
    from twisted.internet import defer
    from twisted.internet.task import react


    @defer.inlineCallbacks
    def example(reactor):
        koji = Connection('brew')
        # Fetch a user.
        # You may pass an ID or a krb principal here
        user = yield koji.getUser(3595)
        # user is a Munch (dict-like) object.
        print(user.name)


    if __name__ == '__main__':
        react(example)

Connecting to a Koji Hub
------------------------

To connect to a Koji hub, create a new ``txkoji.Connection`` instance.

You must pass a string to the constructor. This string is a profile name. For
example, if you call ``Connector('mykoji')``, then txkoji will search
``/etc/koji.conf.d/*.conf`` for the ``[mykoji]`` config section. This matches
what the regular Koji client code does.

Making XML-RPC calls
--------------------

Koji Hub is an XML-RPC server. You can call any method on the ``Connection``
class instance and txkoji will treat it as an XML-RPC call to the hub. For
example, this Twisted ``inlineCallbacks``-style code looks up information about
a given task ID and tag ID:

.. code-block:: python

    @defer.inlineCallbacks
    def example(reactor):
        koji = Connection('mykoji')

        task = yield koji.getTaskInfo(10000)
        print(task.method)  # "createImage"

        tag = yield koji.getTag(2000)
        print(tag.name)  # "foo-build"


To learn the full Koji XML-RPC API::

  koji list-api

You can also read the `koji source code <https://pagure.io/koji/>`_ to find
out details about how each method works.


Logging in
----------

Your Koji hub must support GSSAPI or Client SSL authentication. You must have a
valid Kerberos ticket or SSL keypair.

.. code-block:: python

    @defer.inlineCallbacks
    def example(reactor):
        koji = Connection('mykoji')

        result = yield login()
        print(result)  # "True"
        print('session-id: %s' % koji.session_id)

        # "Who am I?"
        user = yield koji.getLoggedInUser()
        print(user)


Caching long-lived object names
-------------------------------

Sometimes all you have is a user id number or tag id number, and you want the
user's name or tag's name instead.

txkoji includes a read-through cache for obtaining the user name or tag name.
See ``examples/cache.py`` for an example. txkoji's cache module stores its data
in a ``txkoji`` subdirectory of the location specified with the
``$XDG_CACHE_HOME`` environment variable if that is set. It will fall back to
using ``~/.cache/txkoji`` if the ``$XDG_CACHE_HOME`` environment variable is
not set.


Rich objects
------------

The following RPC methods will return special classes that inherit from the
Munch class:

* ``getBuild`` returns ``txkoji.build.Build``
* ``listBuilds`` returns a ``list`` of ``txkoji.build.Build``
* ``getTaskInfo`` returns ``txkoji.task.Task``
* ``getPackage`` returns ``txkoji.package.Package``

These classes have their own special helper methods to implement things I found
interesting:

* ``datetime`` conversions for the start/completion timestamps,
* ``url`` properties for representing the objects in Kojiweb,
* Unified property attributes across task methods, like ``tag``, ``package`` or
  ``is_scratch``.

More special return values:

* ``getAverageBuildDuration`` returns a ``datetime.timedelta`` object instead
  of a raw float, because this is more useful to do time arithmetic.

* The ``task_id`` property is populated on OSBS's CG container builds (a
  workaround for https://pagure.io/koji/issue/215).

Message Parsing
---------------

Koji's messagebus plugin emits messages to an AMQP broker when certain events
happen. The ``txkoji.messages`` module has support for parsing these messages
into the relevant txkoji ``Task`` or ``Build`` classes.


TODO:
=====
* More KojiException subclasses for other possible XML-RPC faults?
* Implement krbV authentication (probably not unless there is an alternative to
  python-krbV).
* `MikeM noted
  <https://lists.fedorahosted.org/archives/list/koji-devel@lists.fedorahosted.org/message/ICFTEETD5MZMDY4S5FWFTO5LPKIAQIVW/>`_,
  the callnum parameter will need special handling. We might need Twisted's
  ``DeferredLock`` to ensure we only have one auth'd RPC in flight at a time.
  It's not really clear to me if we can actually hit a callnum error here. More
  integration testing needed for this.

Packages that use this package
==============================

* `helga-koji <https://github.com/ktdreyer/helga-koji>`_
