import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal, engine, Base
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


async def seed():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == ADMIN_EMAIL))
        if result.scalar_one_or_none():
            print("Admin already exists")
            return
        password = (ADMIN_PASSWORD or "")[:72]
        user = User(
            email=ADMIN_EMAIL,
            hashed_password=pwd_context.hash(password),
            is_admin=True,
        )
        db.add(user)
        await db.commit()
        print(f"Created admin: {ADMIN_EMAIL}")


if __name__ == "__main__":
    asyncio.run(seed())
