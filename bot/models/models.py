# bot/models/models.py
import datetime as dt
import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, Text, text

from bot.core.db import Base


class State(enum.Enum):
    scheduled = "scheduled"
    done = "done"
    deleted = "deleted"


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True)
    title = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    ts_utc = Column(DateTime, nullable=False, default=dt.datetime.utcnow)
    is_all_day = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
    )
    state = Column(Enum(State), default=State.scheduled)
    reminded_24h = Column(Boolean, default=False)
    reminded_90m = Column(Boolean, default=False)


class ChannelPost(Base):
    __tablename__ = "channel_posts"

    id = Column(Integer, primary_key=True)
    tag = Column(String(10), unique=True)  # next_month / month / week / etc.
    message_id = Column(Integer, nullable=False)
