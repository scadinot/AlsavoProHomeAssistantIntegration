"""Tests for the Alsavo Pro protocol layer (no Home Assistant needed)."""
import asyncio

import pytest


class FakeSession:
    """Stand-in for AlsavoSocketCom.

    fail_times: number of connects that fail before succeeding (None = always).
    hang: block forever in connect (to exercise cancellation).
    """

    def __init__(self, ctrl, fail_times=None, hang=False):
        self._ctrl = ctrl
        self.fail_times = fail_times
        self.hang = hang
        self.connects = 0

    async def connect(self, *args):
        self.connects += 1
        if self.hang:
            await asyncio.sleep(3600)
        if self.fail_times is None or self.connects <= self.fail_times:
            raise ConnectionError("boom")

    async def query_all(self):
        return self._ctrl.QueryResponse(1, 1)

    async def set_config(self, idx, value):
        pass


def make_handler(ctrl, session):
    handler = ctrl.AlsavoPro("pac", "123", "127.0.0.1", "1194", "pw")
    handler._session = session
    return handler


def test_payload_get_value_bounds(ctrl):
    payload = ctrl.Payload(0, 1, 6, 0, 0)
    payload.data = (10, 20, 30)
    assert payload.get_value(2) == 30
    assert payload.get_value(3) == 0  # index == len must not raise
    assert payload.get_value(-1) == 0

    payload.startIdx = 5
    assert payload.get_value(4) == 0
    assert payload.get_value(5) == 10
    assert payload.get_value(8) == 0


def test_update_always_failing_raises_and_goes_offline(ctrl, const):
    session = FakeSession(ctrl)
    handler = make_handler(ctrl, session)
    handler._online = True

    with pytest.raises(ConnectionError):
        asyncio.run(handler.update())

    assert not handler._online
    assert session.connects == const.MAX_UPDATE_RETRIES


def test_update_retries_then_succeeds(ctrl):
    session = FakeSession(ctrl, fail_times=1)
    handler = make_handler(ctrl, session)

    asyncio.run(handler.update())

    assert handler.is_online
    assert session.connects == 2


def test_update_cancelled_by_timeout_goes_offline(ctrl):
    handler = make_handler(ctrl, FakeSession(ctrl, hang=True))
    handler._online = True

    async def run():
        async with asyncio.timeout(0.1):
            await handler.update()

    with pytest.raises(TimeoutError):
        asyncio.run(run())
    assert not handler._online


def test_update_has_fresh_retry_budget_per_call(ctrl, const):
    session = FakeSession(ctrl)
    handler = make_handler(ctrl, session)

    for _ in range(3):
        with pytest.raises(ConnectionError):
            asyncio.run(handler.update())

    assert session.connects == 3 * const.MAX_UPDATE_RETRIES


def test_set_config_failure_is_bounded_and_goes_offline(ctrl, const):
    session = FakeSession(ctrl)
    handler = make_handler(ctrl, session)
    handler._online = True

    asyncio.run(handler.set_config(4, 33))

    assert not handler._online
    assert session.connects == const.MAX_SET_CONFIG_RETRIES


def test_set_config_success_marks_online(ctrl):
    handler = make_handler(ctrl, FakeSession(ctrl, fail_times=0))

    asyncio.run(handler.set_config(4, 33))

    assert handler._online


def test_silent_pump_gives_clear_error(ctrl, const, udpclient, monkeypatch):
    calls = 0

    async def no_reply(self, data, timeout=5.0):
        nonlocal calls
        calls += 1
        return None

    monkeypatch.setattr(udpclient.UDPClient, "send_rcv", no_reply)
    handler = ctrl.AlsavoPro("pac", "123", "127.0.0.1", "1194", "pw")

    with pytest.raises(ConnectionError, match="No response to auth request"):
        asyncio.run(handler.update())

    assert not handler.is_online
    assert calls == const.MAX_UPDATE_RETRIES
