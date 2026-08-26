"""
Storage backend for RoomState (game_state.py). Redis-backed in prod (required for
correctness across multiple worker processes, and gives idle-room cleanup for free via
TTL). Falls back to an in-memory dict in dev, matching CHANNEL_LAYERS' dev/prod split —
dev only ever runs a single process, so that's safe there.
"""
import asyncio
from abc import ABC, abstractmethod

from django.conf import settings

from .game_state import RoomState

IDLE_TTL_SECONDS = 60 * 30  # drop room state after 30 minutes of no activity
KEY_PREFIX = "swccg:room:"
LOCK_TIMEOUT_SECONDS = 10  # Redis lock auto-expiry, in case a worker dies mid-hold
LOCK_BLOCKING_TIMEOUT_SECONDS = 5  # how long to wait acquiring before giving up


class RoomStateStore(ABC):
    @abstractmethod
    async def get(self, room_code):
        ...

    @abstractmethod
    async def save(self, room_code, state):
        ...

    @abstractmethod
    async def delete(self, room_code):
        ...

    @abstractmethod
    def lock(self, room_code):
        """Returns an async context manager serializing a room's load-mutate-save
        cycle. Without this, two actions on the same room landing close together (e.g.
        a reconnect racing a real game action) can interleave their load/save calls
        and silently clobber each other's changes — including connected_channels,
        which is how send_hands() knows where to deliver a private hand."""
        ...


class InMemoryRoomStateStore(RoomStateStore):
    def __init__(self):
        self._states = {}
        self._locks = {}

    async def get(self, room_code):
        return self._states.get(room_code)

    async def save(self, room_code, state):
        self._states[room_code] = state

    async def delete(self, room_code):
        self._states.pop(room_code, None)

    def lock(self, room_code):
        # Only guards this one process — correct for dev, which never runs more than
        # one. Never cleaned up (a Lock per room code that's ever existed stays in
        # memory), but each one is tiny, so that's fine at this scale.
        lock = self._locks.get(room_code)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[room_code] = lock
        return lock


class RedisRoomStateStore(RoomStateStore):
    def __init__(self, url):
        import redis.asyncio as redis_asyncio
        self._client = redis_asyncio.Redis.from_url(url, decode_responses=True)

    def _key(self, room_code):
        return f"{KEY_PREFIX}{room_code}"

    async def get(self, room_code):
        raw = await self._client.get(self._key(room_code))
        return RoomState.from_json(raw) if raw is not None else None

    async def save(self, room_code, state):
        # Idle TTL is refreshed on every save, i.e. on every player action.
        await self._client.set(self._key(room_code), state.to_json(), ex=IDLE_TTL_SECONDS)

    async def delete(self, room_code):
        await self._client.delete(self._key(room_code))

    def lock(self, room_code):
        # A real distributed lock — Redis is shared across every worker process, so
        # this closes the gap the in-memory version can't: two of a room's connections
        # landing on different prod workers still can't race each other.
        return self._client.lock(
            f"{KEY_PREFIX}lock:{room_code}",
            timeout=LOCK_TIMEOUT_SECONDS,
            blocking_timeout=LOCK_BLOCKING_TIMEOUT_SECONDS,
        )


_store = None


def get_store():
    global _store
    if _store is None:
        _store = RedisRoomStateStore(settings.GAME_REDIS_URL) if settings.GAME_REDIS_URL else InMemoryRoomStateStore()
    return _store
