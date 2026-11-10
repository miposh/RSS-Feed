"""Tests for /add, /remove, /list — fake bot and DB, no network."""
from types import SimpleNamespace as NS

from aiogram.filters import CommandObject

from app.bot.handlers.user_handlers import cmd_add, cmd_list, cmd_remove

GROUP_ID = -100500
CHANNEL = NS(id=1, channel_id=GROUP_ID, title="Группа")
FEEDS = [NS(id=10, url="https://a/rss", title="A"), NS(id=20, url="https://b/rss", title="B")]


class FakeMessage:
    def __init__(self, chat_type="supergroup", user_id=7, sender_chat=None):
        self.chat = NS(id=GROUP_ID if chat_type != "private" else user_id, type=chat_type)
        self.from_user = NS(id=user_id)
        self.sender_chat = sender_chat
        self.replies = []

    async def reply(self, text, **_):
        self.replies.append(text)

    answer = reply


class FakeBot:
    def __init__(self, status="administrator"):
        self.status = status

    async def get_chat_member(self, chat_id, user_id):
        return NS(status=self.status)


class FakeDB:
    def __init__(self, admin_channels=(CHANNEL,)):
        self.removed, self.added = [], []
        admin_channels = list(admin_channels)

        async def get_channel(channel_id):
            return CHANNEL if channel_id == GROUP_ID else None

        async def get_channels_for_admin(telegram_user_id):
            return admin_channels

        async def get_feeds_by_channel(channel_id):
            return FEEDS

        async def get_feed_by_url(url):
            return NS(id=30, url=url)

        async def add_subscription(feed_id, channel_id):
            self.added.append(feed_id)
            return NS(id=1)

        async def delete_subscription(feed_id, channel_id):
            self.removed.append(feed_id)

        async def noop(**_):
            return None

        self.channels = NS(get_channel=get_channel, get_channels_for_admin=get_channels_for_admin)
        self.rss_feeds = NS(get_feeds_by_channel=get_feeds_by_channel, get_feed_by_url=get_feed_by_url,
                            delete_if_unused=noop)
        self.feed_subscriptions = NS(add=add_subscription, delete=delete_subscription)


def cmd(args):
    return CommandObject(prefix="/", command="x", args=args)


async def test_remove_by_list_number():
    db, msg = FakeDB(), FakeMessage()
    await cmd_remove(msg, cmd("2"), FakeBot(), db)
    assert db.removed == [20]


async def test_remove_by_url():
    db, msg = FakeDB(), FakeMessage()
    await cmd_remove(msg, cmd("https://a/rss"), FakeBot(), db)
    assert db.removed == [10]


async def test_remove_out_of_range_removes_nothing():
    db, msg = FakeDB(), FakeMessage()
    await cmd_remove(msg, cmd("3"), FakeBot(), db)
    assert db.removed == [] and "не найден" in msg.replies[0]


async def test_group_command_rejected_for_non_admin():
    db, msg = FakeDB(), FakeMessage()
    await cmd_add(msg, cmd("https://c/rss"), FakeBot(status="member"), db)
    assert db.added == [] and "администраторам" in msg.replies[0]


async def test_anonymous_admin_allowed():
    db = FakeDB()
    msg = FakeMessage(sender_chat=NS(id=GROUP_ID))
    msg.from_user = None
    await cmd_add(msg, cmd("https://c/rss"), FakeBot(status="member"), db)
    assert db.added == [30]


async def test_add_rejects_non_url():
    db, msg = FakeDB(), FakeMessage()
    await cmd_add(msg, cmd("not-a-url"), FakeBot(), db)
    assert db.added == [] and "Использование" in msg.replies[0]


async def test_private_with_several_groups_asks_to_choose():
    other = NS(id=2, channel_id=-1, title="Другая")
    db, msg = FakeDB(admin_channels=[CHANNEL, other]), FakeMessage(chat_type="private")
    await cmd_add(msg, cmd("https://c/rss"), FakeBot(), db)
    assert db.added == [] and "несколько групп" in msg.replies[0]


async def test_private_with_one_group_applies_to_it():
    db, msg = FakeDB(), FakeMessage(chat_type="private")
    await cmd_add(msg, cmd("https://c/rss"), FakeBot(), db)
    assert db.added == [30]


async def test_list_shows_numbered_feeds():
    db, msg = FakeDB(), FakeMessage()
    await cmd_list(msg, FakeBot(), db)
    assert "1. A" in msg.replies[0] and "2. B" in msg.replies[0]
