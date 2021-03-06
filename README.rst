aiosteady: rate limiting for asyncio
====================================

.. image:: https://img.shields.io/pypi/v/aiosteady.svg
        :target: https://pypi.python.org/pypi/aiosteady

.. image:: https://travis-ci.org/Tinche/aiosteady.svg?branch=master
        :target: https://travis-ci.org/Tinche/aiosteady

.. image:: https://codecov.io/gh/Tinche/aiosteady/branch/master/graph/badge.svg
        :target: https://codecov.io/gh/Tinche/aiosteady

.. image:: https://img.shields.io/pypi/pyversions/aiosteady.svg
        :target: https://github.com/Tinche/aiosteady
        :alt: Supported Python versions

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/ambv/black

**aiosteady** is an Apache2 licensed library, written in Python, for rate limiting
in asyncio application using Redis.

aiosteady currently implements the leaky bucket in a very efficient way.

.. code-block:: python

    throttler = Throttler(aioredis)

    res = await throttler.consume(f'user:{user_id}')


Installation
------------

To install aiosteady, simply:

.. code-block:: bash

    $ pip install aiosteady