from sqlalchemy import (
    BigInteger,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, mapped_column, sessionmaker

from .config import DATABASE_URL


class Base(DeclarativeBase):
    pass


class FollowedUser(Base):
    __tablename__ = "followed_users"

    id = mapped_column(Integer, primary_key=True)
    guild_id = mapped_column(BigInteger, nullable=False)
    channel_id = mapped_column(BigInteger, nullable=False)
    letterboxd_username = mapped_column(String, nullable=False)
    last_diary_entry = mapped_column(DateTime, nullable=True)

    # A user can only be followed once per server channel
    __table_args__ = (
        UniqueConstraint(
            "guild_id",
            "channel_id",
            "letterboxd_username",
            name="_guild_channel_user_uc",
        ),
    )


engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)
