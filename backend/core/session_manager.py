import redis
import uuid
import json
from datetime import timedelta
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
r = redis.from_url(REDIS_URL, decode_responses=True)

SESSION_EXPIRY = timedelta(hours=1)

class SessionManager:
    def __init__(self):
        self.redis_client = r
    
    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self.redis_client.setex(
            f"session:{session_id}:active",
            SESSION_EXPIRY,
            "1"
        )
        return session_id
    
    def session_active(self, session_id: str) -> bool:
        return bool(self.redis_client.exists(f"session:{session_id}:active"))
    
    def get_session_state(self, session_id: str) -> dict:
        state_key = f"session:{session_id}:state"
        state_json = self.redis_client.get(state_key)
        if state_json:
            return json.loads(state_json)
        return None
    
    def set_session_state(self, session_id: str, state: dict):
        state_key = f"session:{session_id}:state"
        self.redis_client.setex(
            state_key,
            SESSION_EXPIRY,
            json.dumps(state)
        )
        self.redis_client.expire(f"session:{session_id}:active", SESSION_EXPIRY)
    
    def close_session(self, session_id: str):
        keys = self.redis_client.keys(f"session:{session_id}:*")
        if keys:
            self.redis_client.delete(*keys)

session_manager = SessionManager()