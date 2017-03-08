import asyncio
import os
import sys
import unittest.mock

import aiohttp

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_until(test, timeout=1.0, loop=None, pre=None):
    """
    Run the event loop until:
        - the test future completes
        - an exception is raised in the test
        - the timeout elapses

    @param test     - coroutine containing the test to run
    @param timeout  - maximum amount of time to wait for the test to complete
    @param loop     - loop to run in
    @param pre      - coroutine to run prior to running the test

    @return         - on success, returns whatever was returned by the test
                      coroutine.  If an exception was raised by the test coroutine, it
                      will be raised once the loop is stopped.  Finally, an
                      asyncio.TimeoutError will be raised if the timeout elapses.
    """
    loop = asyncio.get_event_loop() if loop is None else loop
    done = asyncio.Event(loop=loop)
    exc = None
    ret = None

    async def timer():
        await asyncio.wait_for(
                done.wait(),
                timeout=timeout,
                loop=loop)

    async def test_wrapper():
        nonlocal exc
        nonlocal ret

        if pre is not None:
            await pre

        try:
            ret = await test
        except Exception as e:
            exc = e

        done.set()

    asyncio.ensure_future(test_wrapper(), loop=loop)
    loop.run_until_complete(timer())

    if exc is not None:
        raise exc

    return ret


def mkfuture(ret, return_from=None):
    '''
    Make a asyncio.Future with the result set to `ret`.  If specified,
    `return_from` is assumed to be a unittest.mock.Mock object we can
    set return_value on.
    '''
    f = asyncio.Future()
    f.set_result(ret)

    if return_from is not None:
        assert isinstance(return_from, unittest.mock.Mock)
        return_from.return_value = f
