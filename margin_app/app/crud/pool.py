
import uuid
import asyncio
from decimal import Decimal
from app.models.pool import UserPool
from app.crud.base import DBConnector


class UserPoolCRUD(DBConnector):
    """
    CRUD operations for UserPool model.
    """

    async def create_user_pool(self, user_id, pool_id, token, amount):
        """
        Create a new user pool entry.
        """
        async with self.session() as db:
            user_pool = UserPool(user_id=user_id, pool_id=pool_id, token=token, amount=amount)
            db.add(user_pool)
            await db.commit()
            await db.refresh(user_pool)
            return user_pool

    async def update_user_pool(self, user_pool_id, token=None, amount=None):
        """
        Update user pool details.
        """
        async with self.session() as db:
            user_pool = await db.get(UserPool, user_pool_id)
            if not user_pool:
                return None  # Not found
            
            if token:
                user_pool.token = token
            if amount:
                user_pool.amount = amount

            await db.commit()
            await db.refresh(user_pool)
            return user_pool



# testing
async def test_crud():
    db = UserPoolCRUD()
    
    user_pool = await db.create_user_pool(
        user_id=uuid.uuid4(), pool_id=uuid.uuid4(), token="TEST", amount=Decimal("100.50")
    )
    print("Created:", user_pool)

    updated_pool = await db.update_user_pool(user_pool.id, amount=Decimal("150.75"))
    print("Updated:", updated_pool)

if __name__ == "__main__":
    asyncio.run(test_crud())
