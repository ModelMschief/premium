import motor.motor_asyncio
from datetime import datetime, timezone
import config

# Initialize MongoDB Client
client = motor.motor_asyncio.AsyncIOMotorClient(config.MONGO_URI)
db = client.Payments

banned_collection = db.banned
gem_payments_collection = db.gem_payments
premium_payments_collection = db.premium_payments

async def is_banned(user_id: int) -> bool:
    """Check if the user is in the banned collection."""
    user = await banned_collection.find_one({"user_id": user_id})
    return user is not None

async def save_gem_payment(payment_id: str, user_id: int, username: str, package_name: str, gems_amount: int, stars_amount: int):
    """Save a gem payment to MongoDB."""
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
    await gem_payments_collection.insert_one(document)

async def save_premium_payment(payment_id: str, user_id: int, username: str, package_name: str, duration_days: int, stars_amount: int):
    """Save a premium payment to MongoDB."""
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
    await premium_payments_collection.insert_one(document)
