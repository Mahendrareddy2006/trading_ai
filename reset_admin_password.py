
from getpass import getpass

from trading_ai.core.security import hash_password
from trading_ai.database.models import User
from trading_ai.database.session import SessionLocal

email = "admin@tradingai.local"

db = SessionLocal()
try:
    user = db.query(User).filter(User.email == email).first()

    if user is None:
        print("Admin account not found.")
    else:
        new_password = getpass("Enter your new admin password: ")
        confirm_password = getpass("Confirm your new password: ")

        if len(new_password) < 12:
            print("Password must be at least 12 characters.")
        elif new_password != confirm_password:
            print("Passwords do not match.")
        else:
            user.hashed_password = hash_password(new_password)
            db.commit()
            print("Admin password reset successfully.")
finally:
    db.close()
