=============================================================
Stripe API bindings for Python 3.5+ using asyncio and aiohttp
=============================================================

.. image:: https://travis-ci.org/jsbronder/asyncio_stripe.svg?branch=master
    :target: https://travis-ci.org/jsbronder/asyncio_stripe

Unmaintained
------------
This project is no longer actively maintained.

Introduction
------------
As the header says, this is a wrapper around the Stripe API using asyncio_ and
aiohttp_.  Stripe data is modeled using frozen objects built using attrs_.
Required arguments to API calls are explicitly listed while optional arguments
are simply keyword arguments.

Installation
------------
asyncio_stripe be installed via pip or by simply running the included
``setup.py`` script::

    pip install asyncio_stripe
    # OR
    python setup.py install --root <destination> --record installed_files.txt

Examples
--------

Create a Client:

.. code-block:: python

    import aiohttp
    import asyncio_stripe

    session = aiohttp.ClientSession()
    client = asyncio_stripe.Client(session, 'sk_test_aabbcc')

Authorize then capture $1.00 from a Customer's default card:

.. code-block:: python

    auth = await client.create_charge(
        amount=100,
        currency='usd',
        description='Creating a test charge',
        customer=customer_id,
        capture=False)

    charge = await client.capture_charge(charge.id)

Capture funds using a token:

.. code-block:: python

    charge = await client.create_charge(
        amount=100,
        currency='usd',
        description='Capturing with a token',
        source='tok_aabbcc')

Create, retrieve and pretty print a customer:

.. code-block:: python

    import pprint
    import attr

    customer = await client.create_customer(
        email='new_user@invalid',
        source='tok_aabbcc')

    ret_customer = await client.retrieve_customer(
        customer.id)

    customers = await client.list_customers(limit=1)

    assert(customer == ret_customer == customers[0])
    pprint.pprint(attr.asdict(customer))

Thanks
------
While this project represents the company in no way, thanks to Kuvée
(https://kuvee.com) for generously sponsoring some of the time I've spent in
development.


.. _asyncio: https://docs.python.org/3/library/asyncio.html
.. _aiohttp: https://github.com/aio-libs/aiohttp
.. _attrs: https://github.com/python-attrs/attrs
