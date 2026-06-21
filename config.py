import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
TARGET_BOT_USERNAME = os.getenv("TARGET_BOT_USERNAME", "anoni67_bot")
ADMIN_ID = 1928631932 # Admin ID to notify on successful payments
BSC_API_KEY = os.getenv("BSC_API_KEY")
BSC_RECEIVING_ADDRESS = os.getenv("BSC_RECEIVING_ADDRESS")

# Pricing Configuration
GEMS_PACKAGES = [
    {"name": "100 Gems", "gems": 100, "stars": 50, "USDT":1},
    {"name": "500 Gems", "gems": 500, "stars": 230, "USDT":4.5},
    {"name": "1000 Gems", "gems": 1000, "stars": 450, "USDT":9},
    {"name": "2000 Gems", "gems": 2000, "stars": 900, "USDT":17},
]

PREMIUM_PACKAGES = [
    {"name": "30 Days ", "duration_days": 30, "stars": 120, "USDT":4},
    {"name": "60 Days ", "duration_days": 60, "stars": 220, "USDT":7},
    {"name": "90 Days ", "duration_days": 90, "stars": 340, "USDT":12},
    {"name": "365 Days ", "duration_days": 365, "stars": 1250, "USDT":34},
]

# Conversion rate for custom gems (e.g., 2 Gems = 1 Star)
# Formula: Stars = math.ceil(gems / GEMS_PER_STAR)
GEMS_PER_STAR = 2

# Group Messaging Subscriptions Configuration
SUPPORTED_GROUPS = [-1003089721365,-1002613165023,-1003593973822,-1002005837283] # Replace with actual group IDs

GROUP_SUB_PACKAGES = [
    {"name": "7 Days", "duration_days": 7, "stars": 50},
    {"name": "30 Days", "duration_days": 30, "stars": 175},
    {"name": "90 Days", "duration_days": 90, "stars": 450},
    {"name": "365 Days", "duration_days": 365, "stars": 1500},
]

# ─── Multi-Tenant Clone Feature ───────────────────────────────
PLATFORM_RECEIVING_ADDRESS = os.getenv("PLATFORM_RECEIVING_ADDRESS", "0x373A1C056a3EC15a40CFB88170Cf3C58bc0bf7B8")
CLONE_SLOT_STARS_PRICE = 25      # Stars for +5 clone slots
CLONE_SLOT_USDT_PRICE = 5        # USDT for +5 clone slots
CREATOR_REVENUE_SHARE = 0.90     # 90% to creator, 10% to platform
MAIN_BOT_USERNAME = os.getenv("MAIN_BOT_USERNAME", "")  # Filled dynamically on startup
