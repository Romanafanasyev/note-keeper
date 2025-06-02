# bot/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, Boolean
from bot.db import Base
import enum, datetime as dt

class State(enum.Enum):
    scheduled = "scheduled"
    done      = "done"
    deleted   = "deleted"

class Plan(Base):
    __tablename__ = "plans"

    id           = Column(Integer, primary_key=True)
    title        = Column(String(120), nullable=False)
    description  = Column(Text, nullable=True)
    ts_utc       = Column(DateTime, nullable=False, default=dt.datetime.utcnow)
    state        = Column(Enum(State), default=State.scheduled)
    reminded_24h = Column(Boolean, default=False)
    reminded_90m = Column(Boolean, default=False)

class ChannelPost(Base):
    __tablename__ = "channel_posts"

    id         = Column(Integer, primary_key=True)
    tag        = Column(String(10), unique=True)   # month / week / tomorrow / today
    message_id = Column(Integer, nullable=False)
