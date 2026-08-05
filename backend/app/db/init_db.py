"""
Creates all database tables and seeds a default admin user on first run.
Safe to call multiple times (idempotent).
"""
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models.user import User, UserRole
from app.core.security import hash_password
from app.core.logging_config import logger


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified.")

    db = SessionLocal()
    try:
        existing_admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if not existing_admin:
            admin = User(
                full_name="Platform Administrator",
                email="admin@salesbi.local",
                hashed_password=hash_password("Admin@123"),
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            logger.info(
                "Seeded default admin user -> email: admin@salesbi.local | "
                "password: Admin@123  (CHANGE THIS IMMEDIATELY AFTER FIRST LOGIN)"
            )
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
