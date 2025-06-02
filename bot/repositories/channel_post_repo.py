# bot/repositories/channel_post_repo.py
from sqlalchemy.orm import Session
from bot.repositories.base_repo import BaseRepo
from bot.models.models import ChannelPost

class ChannelPostRepo(BaseRepo[ChannelPost]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, ChannelPost)
