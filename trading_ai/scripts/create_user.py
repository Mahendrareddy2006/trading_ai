"""Admin User Provisioning CLI Script.

Usage:
    py trading_ai/scripts/create_user.py --email admin@tradingai.local --username admin --password MyPassword123! --admin
"""

import argparse
import sys
import uuid
from pathlib import Path

# Ensure trading_ai is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from trading_ai.core.security import hash_password
from trading_ai.database.models import User
from trading_ai.database.session import SessionLocal, init_db


def create_user(email: str, username: str, password: str, is_admin: bool = False):
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(User).filter((User.email == email) | (User.username == username)).first()
        if existing:
            print(f"[ERROR] User with email '{email}' or username '{username}' already exists (ID: {existing.id}).")
            return existing

        user = User(
            id=str(uuid.uuid4()),
            email=email.strip().lower(),
            username=username.strip(),
            hashed_password=hash_password(password),
            is_active=True,
            is_superuser=is_admin
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"[SUCCESS] User '{username}' ({email}) created successfully with ID: {user.id} (Admin: {is_admin})")
        return user
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provision a new user account in Trading AI.")
    parser.add_argument("--email", required=True, help="User email address")
    parser.add_argument("--username", required=True, help="User username")
    parser.add_argument("--password", required=True, help="User plaintext password (will be scrypt-hashed)")
    parser.add_argument("--admin", action="store_true", help="Grant administrator privileges")

    args = parser.parse_args()
    create_user(args.email, args.username, args.password, args.admin)
