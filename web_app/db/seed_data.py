"""
Seed data for initializing the database with predefined values.
"""
from faker import Faker
from sqlalchemy.orm import Session
from .models import Status, User, Position, AirDrop, TelegramUser
from .database import Base, engine, SessionLocal
from decimal import Decimal
from typing import List

# Initialize Faker
fake = Faker()

def create_users(session: Session) -> List[User]:
    """
    Create and save a list of fake users to the database.
    Args:
        session (Session): SQLAlchemy session object.
    Returns:
        list[User]: A list of User objects added to the database.
    """
    users = []
    for _ in range(10):
        user = User(
            wallet_id=fake.unique.uuid4(),
            contract_address=fake.address(),
            is_contract_deployed=fake.boolean()
        )
        users.append(user)
    session.add_all(users)
    session.commit()
    return users

def create_positions(session: Session, users: List[User]) -> None:
    """
    Create and save fake position records associated with given users.
    Args:
        session (Session): SQLAlchemy session object.
        users (list): List of User objects to associate with positions.
    """
    positions = []
    for user in users:
        for _ in range(10):
            position = Position(
                user_id=user.id,
                token_symbol=fake.word(),
                amount=fake.random_number(digits=5),
                multiplier=fake.random_int(min=1, max=10),
                start_price=Decimal(fake.pydecimal(left_digits=5, right_digits=2, positive=True)),                
                status=fake.random_element(elements=[status.value for status in Status]),
            )
            positions.append(position)
    if positions:
        session.bulk_save_objects(positions)
        session.commit()
        print(f"Created {len(positions)} positions for {len(users)} users.")
    else:
        print("No positions created.")

def create_airdrops(session: Session, users: List[User]) -> None:
    """
    Create and save fake airdrop records for each user.
    Args:
        session (Session): SQLAlchemy session object.
        users (list): List of User objects to associate with airdrops.
    """
    airdrops = []
    for user in users:
        for _ in range(10):
            airdrop = AirDrop(
                user_id=user.id,
                amount=Decimal(fake.pydecimal(left_digits=5, right_digits=2, positive=True)),
                is_claimed=fake.boolean(),
                claimed_at=fake.date_time_this_decade() if fake.boolean() else None,
            )
            airdrops.append(airdrop)
    if airdrops:
        session.bulk_save_objects(airdrops)
        session.commit()

def create_telegram_users(session: Session, users: List[User]) -> None:
    """
    Create and save fake Telegram user records to the database.
    Args:
        session (Session): SQLAlchemy session object.
    """
    telegram_users = []
    for user in users:
        for _ in range(10):
            telegram_user = TelegramUser(
                telegram_id=fake.unique.uuid4(),
                username=fake.user_name(),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                wallet_id=user.wallet_id,
                photo_url=fake.image_url(),
            )
            telegram_users.append(telegram_user)
    session.bulk_save_objects(telegram_users)
    session.commit()
    print(f"Created {len(telegram_users)} Telegram users.")

if __name__ == '__main__':
    # Start a new session for seeding data
    with SessionLocal() as session:
        # Populate the database
        users = create_users(session)
        create_positions(session, users)
        create_airdrops(session, users)
        create_telegram_users(session, users)

print("Database populated with fake data.")
