import asyncio
from aiogram import Router, Dispatcher

router = Router()

dp1 = Dispatcher()
dp1.include_router(router)

dp2 = Dispatcher()
try:
    dp2.include_router(router)
    print("Success")
except Exception as e:
    print(f"Error: {e}")
