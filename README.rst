aiosteady: rate limiting for asyncio
====================================

.. image:: https://img.shields.io/pypi/v/aiosteady.svg
        :target: https://pypi.python.org/pypi/aiosteady

.. image:: https://github.com/Tinche/aiosteady/workflows/CI/badge.svg
        :target: https://github.com/Tinche/aiosteady/actions?workflow=CI

.. image:: https://codecov.io/gh/Tinche/aiosteady/branch/master/graph/badge.svg
        :target: https://codecov.io/gh/Tinche/aiosteady

.. image:: https://img.shields.io/pypi/pyversions/aiosteady.svg
        :target: https://github.com/Tinche/aiosteady
        :alt: Supported Python versions

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/ambv/black


----

**aiosteady** is an MIT licensed library, written in Python, for rate limiting
in asyncio applications using Redis and the aioredis_ library.

aiosteady currently implements the `leaky bucket algorithm`_ in a very efficient way.

.. code-block:: python

    max_capacity = 10  # The bucket can contain up to 10 drops, starts with 0
    drop_recharge = 5.0  # 5 seconds between drop recharges.
    throttler = Throttler(aioredis, max_capacity, drop_recharge)

    # consume() returns information about success, the current bucket level,
    # how long until the next drop recharges, etc.
    res = await throttler.consume(f'user:{user_id}')

.. _aioredis: https://github.com/aio-libs/aioredis
.. _`leaky bucket algorithm`: https://en.wikipedia.org/wiki/Leaky_bucket

Installation
------------

To install aiosteady, simply:

.. code-block:: bash

    $ pip install aiosteady


Usage
-----

The leaky bucket algorithm follows a simple model.

* A single bucket contains a number of drops, called the bucket level. Buckets start with zero drops.
* Buckets have a maximum capacity of drops.
* Each use of the bucket (consumption) inserts one or more drops into the bucket, up until the maximum capacity. If the bucket would overflow, the consumption fails.
* One drop leaks out every `drop_recharge` seconds, freeing space in the bucket for a new drop to be put into it.
* The bucket may also be manually drained.

* In addition to making the consumption fail, full buckets can optionally be configured to block further attempts to consume for a period.

Create an instance of ``aiosteady.leakybucket.Throttler``, giving it an instance
of an ``aioredis`` client and rate limiting parameters (the maximum bucket
capacity, the number of seconds it takes for a drop to leak out, and an
optional blocking duration).

A ``Throttler`` supports two operations: consuming and peeking.

* ``await Throttler.consume("a_key")`` (``consume`` because it consumes bucket resources)
  attempts to put the given number of drops (default 1) into the bucket at the
  given key. It returns an instance of ``aiosteady.leakybucket.ThrottleResult``,
  with fields for:

  * ``success``: a boolean, describing whether the consumption was successful
  * ``level``: an integer, describing the new level of the bucket
  * ``until_next_drop``: a float, describing the number of seconds left after the next drop regenerates
  * ``blocked_for``: an optional float, if blocking is being used and the bucket is blocked, the number of seconds until the block expires

  If the number of drops given is negative, drops are instead removed from the bucket. The bucket may not go below zero drops.

* ``await Throttler.peek("a_key")`` returns the same ``ThrottleResult`` but without attempting to
  consume any drops.

Both operations are implemented using a single Redis call, using Lua scripting.

Changelog
---------

22.1.0 (UNRELEASED)
~~~~~~~~~~~~~~~~~~~
* Switch to CalVer.
* Add Python 3.10 support.
* Add support for recharging the bucket (removing existing drops).
* Switch the main branch name from `master` to `main`.


0.2.1 (2021-05-12)
~~~~~~~~~~~~~~~~~~
* Improve the ``attrs`` dependency specification, since ``attrs`` uses CalVer.

0.2.0 (2021-04-08)
~~~~~~~~~~~~~~~~~~
* Use the Redis ``evalsha`` instead of ``eval``, for efficiency.

0.1.0 (2021-03-07)
~~~~~~~~~~~~~~~~~~
* Initial release.

Credits
-------

The Lua Redis script for atomic leaky bucket has been taken and heavily adapted from the Prorate_ project.

.. _Prorate: https://github.com/WeTransfer/prorate
