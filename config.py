import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
TARGET_BOT_USERNAME = os.getenv("TARGET_BOT_USERNAME", "anoni67_bot")

# Pricing Configuration
GEMS_PACKAGES = [
    {"name": "100 Gems", "gems": 100, "stars": 50},
    {"name": "500 Gems", "gems": 500, "stars": 250},
    {"name": "1000 Gems", "gems": 1000, "stars": 500},
]

PREMIUM_PACKAGES = [
    {"name": "30 Days Premium", "duration_days": 30, "stars": 1},
    {"name": "90 Days Premium", "duration_days": 90, "stars": 360},
    {"name": "365 Days Premium", "duration_days": 365, "stars": 1250},
]

# Conversion rate for custom gems (e.g., 2 Gems = 1 Star)
# Formula: Stars = math.ceil(gems / GEMS_PER_STAR)
GEMS_PER_STAR = 2
