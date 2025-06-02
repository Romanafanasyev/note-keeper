# bot/services/channel_post_service.py
from typing import Dict

from bot.models.models import ChannelPost
from bot.repositories.channel_post_repo import ChannelPostRepo
from bot.services.dtos import CreateChannelPostDTO


class ChannelPostService:
    def __init__(self, repo: ChannelPostRepo):
        self.repo = repo

    def create_channel_post(self, dto: CreateChannelPostDTO) -> ChannelPost:
        post = ChannelPost(tag=dto.tag, message_id=dto.message_id)
        return self.repo.create(post)

    def get_all_posts(self) -> Dict[str, int]:
        posts = self.repo.list_all()
        return {post.tag: post.message_id for post in posts}
