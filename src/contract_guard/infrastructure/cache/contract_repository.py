"""Asynchronous Redis repository for volatile, owner-scoped contracts."""

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError, ResponseError, WatchError

from contract_guard.config.settings import Settings


class ContractStorageError(RuntimeError):
    """Raised when the volatile contract store cannot complete an operation."""


class ContractNotFoundError(LookupError):
    """Raised for missing, expired, or non-owner contract access."""


class ContractCapacityError(ContractStorageError):
    """Raised when the configured active-contract limit is reached."""


class TemporaryContractRepository:
    """Store each contract as one TTL-bound JSON value in dedicated Redis."""

    _CREATE_SCRIPT = """
local now = tonumber(ARGV[1])
redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', now)
if redis.call('ZCARD', KEYS[2]) >= tonumber(ARGV[2]) then return 0 end
if redis.call('SET', KEYS[1], ARGV[3], 'EX', ARGV[4], 'NX') == false then return -1 end
redis.call('ZADD', KEYS[2], now + tonumber(ARGV[4]), ARGV[5])
redis.call('EXPIRE', KEYS[2], ARGV[4])
return 1
"""
    _DELETE_SCRIPT = """
local payload = redis.call('GET', KEYS[1])
if not payload then return 0 end
local owner = cjson.decode(payload)['owner_id']
if owner ~= ARGV[1] then return -1 end
redis.call('DEL', KEYS[1])
redis.call('ZREM', KEYS[2], ARGV[2])
return 1
"""

    def __init__(self, client: Redis | None = None, settings: Settings | None = None):
        """Initialize the repository with an injectable async Redis client."""
        self.settings = settings or Settings()
        self.client = client or Redis.from_url(
            self.settings.contract_redis_url,
            decode_responses=True,
            socket_connect_timeout=self.settings.redis_socket_timeout_seconds,
            socket_timeout=self.settings.redis_socket_timeout_seconds,
        )

    def _key(self, contract_id: str) -> str:
        """Build a namespaced contract key."""
        return f"contract_guard:contract:{contract_id}"

    def _owner_key(self, owner_id: str) -> str:
        """Build an owner index key used only for active-limit enforcement."""
        return f"contract_guard:contract-owner:{owner_id}"

    async def create_contract(self, contract: dict[str, Any]) -> None:
        """Create a contract without allowing eviction or duplicate identifiers."""
        try:
            result = await self.client.eval(
                self._CREATE_SCRIPT, 2, self._key(contract["contract_id"]), self._owner_key(contract["owner_id"]),
                int(datetime.now(UTC).timestamp()), self.settings.contract_max_active_per_user,
                json.dumps(contract, ensure_ascii=False, allow_nan=False), self.settings.contract_ttl_seconds,
                contract["contract_id"],
            )
        except (RedisError, ValueError, TypeError) as exc:
            raise ContractStorageError("Temporary contract storage is unavailable") from exc
        if result == 0:
            raise ContractCapacityError("Active contract limit reached")
        if result != 1:
            raise ContractStorageError("Could not create temporary contract")

    async def get_contract(self, contract_id: str, owner_id: str) -> dict[str, Any]:
        """Return a current contract only when it belongs to the requesting owner."""
        try:
            payload = await self.client.get(self._key(contract_id))
        except RedisError as exc:
            raise ContractStorageError("Temporary contract storage is unavailable") from exc
        if payload is None:
            raise ContractNotFoundError("Contract is absent or expired")
        contract = json.loads(payload)
        if contract["owner_id"] != str(owner_id):
            raise ContractNotFoundError("Contract is absent or expired")
        return contract

    async def update_contract(self, contract_id: str, owner_id: str, update: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        """Atomically update a contract while preserving its original TTL."""
        key = self._key(contract_id)
        for _ in range(3):
            try:
                async with self.client.pipeline(transaction=True) as pipe:
                    await pipe.watch(key)
                    payload = await pipe.get(key)
                    ttl = await pipe.ttl(key)
                    if payload is None or ttl <= 0:
                        raise ContractNotFoundError("Contract is absent or expired")
                    contract = json.loads(payload)
                    if contract["owner_id"] != str(owner_id):
                        raise ContractNotFoundError("Contract is absent or expired")
                    update(contract)
                    pipe.multi()
                    pipe.set(key, json.dumps(contract, ensure_ascii=False, allow_nan=False), keepttl=True)
                    await pipe.execute()
                    return contract
            except WatchError:
                continue
            except ContractNotFoundError:
                raise
            except (RedisError, ValueError, TypeError) as exc:
                raise ContractStorageError("Temporary contract storage is unavailable") from exc
        raise ContractStorageError("Temporary contract was updated concurrently")

    async def delete_contract(self, contract_id: str, owner_id: str) -> None:
        """Delete an owner-scoped contract and its active-index entry."""
        try:
            result = await self.client.eval(self._DELETE_SCRIPT, 2, self._key(contract_id), self._owner_key(str(owner_id)), str(owner_id), contract_id)
        except RedisError as exc:
            raise ContractStorageError("Temporary contract storage is unavailable") from exc
        if result != 1:
            raise ContractNotFoundError("Contract is absent or expired")

    async def get_contract_ttl(self, contract_id: str, owner_id: str) -> int:
        """Return remaining TTL after enforcing ownership."""
        await self.get_contract(contract_id, owner_id)
        try:
            ttl = await self.client.ttl(self._key(contract_id))
        except RedisError as exc:
            raise ContractStorageError("Temporary contract storage is unavailable") from exc
        if ttl <= 0:
            raise ContractNotFoundError("Contract is absent or expired")
        return ttl
