"""
Storage backend for RoomState (game_state.py). Redis-backed in prod (required for
correctness across multiple worker processes, and gives idle-room cleanup for free via
TTL). Falls back to an in-memory dict in dev, matching CHANNEL_LAYERS' dev/prod split —
dev only ever runs a single process, so that's safe there.
"""
from abc import ABC, abstractmethod

from django.conf import settings

from .game_state import RoomState

IDLE_TTL_SECONDS = 60 * 30  # drop room state after 30 minutes of no activity
KEY_PREFIX = "swccg:room:"


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


class InMemoryRoomStateStore(RoomStateStore):
    def __init__(self):
        self._states = {}

    async def get(self, room_code):
        return self._states.get(room_code)

    async def save(self, room_code, state):
        self._states[room_code] = state

    async def delete(self, room_code):
        self._states.pop(room_code, None)


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


_store = None


def get_store():
    global _store
    if _store is None:
        _store = RedisRoomStateStore(settings.GAME_REDIS_URL) if settings.GAME_REDIS_URL else InMemoryRoomStateStore()
    return _store
