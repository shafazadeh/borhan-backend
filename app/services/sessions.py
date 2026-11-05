import json

import redis


SESSION_SECONDS = 7200


class SessionStore:
    def __init__(self, redis_url: str):
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)

    @staticmethod
    def key(user_id: str, contract_id: str) -> str:
        return f"contract:{user_id}:{contract_id}"

    def save(self, user_id: str, session: dict) -> None:
        self.client.set(self.key(user_id, session["contract_id"]), json.dumps(session, ensure_ascii=False), ex=SESSION_SECONDS)

    def get(self, user_id: str, contract_id: str) -> dict | None:
        script = "local v=redis.call('GET',KEYS[1]); if not v then return nil end; return {v,redis.call('TTL',KEYS[1])}"
        result = self.client.eval(script, 1, self.key(user_id, contract_id))
        if not result:
            return None
        session = json.loads(result[0])
        session["expires_in_seconds"] = max(0, int(result[1]))
        return session

    def delete(self, user_id: str, contract_id: str) -> bool:
        return bool(self.client.delete(self.key(user_id, contract_id)))
