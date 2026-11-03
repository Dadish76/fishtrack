import os

from sqlalchemy.dialects.postgresql import insert

from .database import SessionLocal, hash_password
from .models import User


def main():
    password = os.environ.get("ADMIN_PASSWORD", "")

    if len(password) < 12:
        raise SystemExit("ADMIN_PASSWORD must contain at least 12 characters")

    with SessionLocal() as db:
        statement = (
            insert(User)
            .values(
                username="admin",
                hashed_password=hash_password(password),
                is_admin=True,
            )
            .on_conflict_do_nothing(index_elements=[User.username])
        )

        result = db.execute(statement)
        db.commit()

        if result.rowcount == 1:
            print("Initial administrator created")
        else:
            print("Initial administrator already exists")


if __name__ == "__main__":
    main()
