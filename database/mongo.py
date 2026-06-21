import motor.motor_asyncio
from datetime import datetime, timezone
import config

_client = None
_db = None
_banned_collection = None
_gem_payments_collection = None
_premium_payments_collection = None

def get_db():
    global _client, _db, _banned_collection, _gem_payments_collection, _premium_payments_collection
    if _client is None:
        _client = motor.motor_asyncio.AsyncIOMotorClient(config.MONGO_URI)
        _db = _client.Payments
        _banned_collection = _db.banned
        _gem_payments_collection = _db.gem_payments
        _premium_payments_collection = _db.premium_payments
    return _db

async def is_banned(user_id: int) -> bool:
    """Check if the user is in the banned collection."""
    get_db() # Ensures initialization happens inside the active event loop
    user = await _banned_collection.find_one({"user_id": user_id})
    return user is not None

async def save_gem_payment(payment_id: str, user_id: int, username: str, package_name: str, gems_amount: int, stars_amount: int):
    """Save a gem payment to MongoDB."""
    get_db() # Ensures initialization happens inside the active event loop
    document = {
        "payment_id": payment_id,
        "user_id": user_id,
        "username": username,
        "package_name": package_name,
        "gems_amount": gems_amount,
        "stars_amount": stars_amount,
        "status": "completed",
        "claimed": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await _gem_payments_collection.insert_one(document)

async def save_premium_payment(payment_id: str, user_id: int, username: str, package_name: str, duration_days: int, stars_amount: int):
    """Save a premium payment to MongoDB."""
    get_db() # Ensures initialization happens inside the active event loop
    document = {
        "payment_id": payment_id,
        "user_id": user_id,
        "username": username,
        "package_name": package_name,
        "duration_days": duration_days,
        "stars_amount": stars_amount,
        "status": "completed",
        "claimed": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await _premium_payments_collection.insert_one(document)
