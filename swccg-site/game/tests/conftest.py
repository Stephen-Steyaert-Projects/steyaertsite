import pytest
from channels.layers import channel_layers

import game.state_store as state_store


@pytest.fixture(autouse=True)
def reset_game_state_store():
    """The in-memory RoomState store is a module-level singleton — reset it between
    tests so state from one test's room codes can't bleed into another's."""
    state_store._store = None
    yield
    state_store._store = None


@pytest.fixture(autouse=True)
def reset_channel_layer():
    """channels.layers.channel_layers caches the InMemoryChannelLayer instance
    process-wide — reset it between tests so no state (queued messages, group
    membership) leaks from one test's room codes into another's."""
    channel_layers.backends = {}
    yield
    channel_layers.backends = {}


@pytest.fixture
async def comms():
    """Tracks every WebsocketCommunicator a test opens (via .connect(...)) and force-
    disconnects all of them on teardown, even if the test fails an assertion partway
    through — otherwise a communicator left connected leaves its consumer's background
    task running into the next test."""
    created = []

    async def _connect(room, user):
        from channels.testing import WebsocketCommunicator
        from game.consumers import RoomConsumer

        communicator = WebsocketCommunicator(RoomConsumer.as_asgi(), f"/ws/game/{room.code}/")
        communicator.scope["url_route"] = {"kwargs": {"room_code": room.code}}
        communicator.scope["user"] = user
        connected, _ = await communicator.connect()
        assert connected
        created.append(communicator)
        return communicator

    yield _connect

    for communicator in created:
        try:
            await communicator.disconnect(timeout=10)
        except Exception:
            pass
