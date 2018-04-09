Async interface to Koji, using Twisted
======================================

.. image:: https://travis-ci.org/ktdreyer/txkoji.svg?branch=master
             :target: https://travis-ci.org/ktdreyer/txkoji

.. image:: https://badge.fury.io/py/txkoji.svg
             :target: https://badge.fury.io/py/txkoji

Access Koji's XML-RPC API asynchronously (non-blocking) using the Twisted
framework.

For now this only supports unauthenticated access.

Simple Example: Fetching a user's name
--------------------------------------

.. code-block:: python

    from txkoji import Connection, KojiException
    from twisted.internet import defer, reactor


    @defer.inlineCallbacks
    def example():
        koji = Connection('brew')
        # fetch a user
        try:
            # you may pass an ID or a krb principal here
            user = yield koji.getUser(3595)
            # user is a Munch (dict-like) object.
            print(user.name)
        except KojiException as e:
            print(e)


    if __name__ == '__main__':
        example().addCallback(lambda ign: reactor.stop())
        reactor.run()

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
    def example():
        koji = Connection('mykoji')

        task = yield koji.getTaskInfo(10000)
        print(task.method)  # "createImage"

        tag = yield koji.getTag(2000)
        print(tag.name)  # "foo-build"


To learn the full Koji XML-RPC API::

  koji list-api

You can also read the `koji source code <https://pagure.io/koji/>`_ to find
out details about how each method works.


Rich objects
------------

The following RPC methods will return special classes that inherit from the
Munch class:

* ``getBuild`` returns ``txkoji.build.Build``
* ``listBuilds`` returns a ``list`` of ``txkoji.build.Build``
* ``getTaskInfo`` returns ``txkoji.task.Task``
* ``getPackage`` returns ``txkoji.package.Package``

These classes have their own special helper methods to implement things I found
interesting, like ``datetime`` conversions for the start/completion timestamps,
or ``url`` properties for representing the objects in Kojiweb.

More special return values:

* ``getAverageBuildDuration`` returns a ``datetime.timedelta`` object instead
  of a raw float, because this is more useful to do time arithmetic.


TODO:
=====
* More KojiException subclasses for other possible XML-RPC faults?
* Implement authentication (low priority). As `MikeM noted
  <https://lists.fedorahosted.org/archives/list/koji-devel@lists.fedorahosted.org/message/ICFTEETD5MZMDY4S5FWFTO5LPKIAQIVW/>`_,
  the callnum parameter will need special handling. (Maybe use Twisted's
  ``DeferredLock`` to ensure we only have one auth'd RPC in flight at a time?)
