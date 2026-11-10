import html

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import BotCommand, BotCommandScopeAllChatAdministrators, BotCommandScopeAllPrivateChats, Message
from aiogram_dialog import DialogManager, StartMode

from app.bot.dialogs.flows.main.states import MainSG
from app.infrastructure.database.db import DB
from app.infrastructure.database.models.channel import ChannelModel
from app.services.chat_service import ChatService

commands_router = Router()

GROUP_TYPES = ("group", "supergroup")

HELP_TEXT = (
    "<b>Команды</b>\n\n"
    "/list — список источников\n"
    "/add &lt;url&gt; — добавить RSS-источник\n"
    "/remove &lt;номер или url&gt; — удалить источник (номер из /list)\n"
    "/help — эта справка\n\n"
    "В группе команды работают для её администраторов. "
    "В личке — для вашей группы, если она одна; иначе используйте меню /start."
)

BOT_COMMANDS = [
    BotCommand(command="list", description="Список источников"),
    BotCommand(command="add", description="Добавить источник: /add <url>"),
    BotCommand(command="remove", description="Удалить источник: /remove <номер>"),
    BotCommand(command="help", description="Справка по командам"),
]


async def set_bot_commands(bot: Bot) -> None:
    """Show the command menu in private chats and to group admins."""
    private = [BotCommand(command="start", description="Меню управления"), *BOT_COMMANDS]
    await bot.set_my_commands(private, scope=BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(BOT_COMMANDS, scope=BotCommandScopeAllChatAdministrators())


async def _is_group_admin(message: Message, bot: Bot) -> bool:
    # Anonymous admins post on behalf of the group itself.
    if message.sender_chat and message.sender_chat.id == message.chat.id:
        return True
    if not message.from_user:
        return False
    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    return member.status in ("administrator", "creator")


async def _resolve_channel(message: Message, bot: Bot, db: DB) -> ChannelModel | None:
    """Pick the group a command applies to, replying with the reason when there is none."""
    if message.chat.type in GROUP_TYPES:
        if not await _is_group_admin(message, bot):
            await message.reply("❌ Команда доступна только администраторам группы")
            return None
        channel = await db.channels.get_channel(channel_id=message.chat.id)
        if not channel:
            await message.reply("❌ Группа не подключена. Выдайте боту права администратора.")
        return channel

    channels = await db.channels.get_channels_for_admin(telegram_user_id=message.from_user.id) or []
    if len(channels) == 1:
        return channels[0]
    if not channels:
        await message.answer("❌ У вас нет подключённых групп. Добавьте бота в группу через /start.")
    else:
        await message.answer("У вас несколько групп — отправьте команду в нужной группе или используйте /start.")
    return None


def _format_feeds(feeds) -> str:
    return "\n".join(
        f"{i}. {html.escape(feed.title or 'Без названия')}\n   {html.escape(feed.url)}"
        for i, feed in enumerate(feeds, 1)
    )


@commands_router.message(CommandStart(), F.chat.type == "private")
async def process_rss_command(
    message: Message,
    dialog_manager: DialogManager,
) -> None:
    await dialog_manager.start(state=MainSG.rss_parser, mode=StartMode.RESET_STACK)


@commands_router.message(Command("help", "start"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@commands_router.message(Command("list"))
async def cmd_list(message: Message, bot: Bot, db: DB) -> None:
    chat_service = ChatService(db)

    if message.chat.type in GROUP_TYPES:
        channel = await _resolve_channel(message, bot, db)
        channels = [channel] if channel else []
    else:
        channels = await db.channels.get_channels_for_admin(telegram_user_id=message.from_user.id) or []
        if not channels:
            await message.answer("❌ У вас нет подключённых групп. Добавьте бота в группу через /start.")
            return

    blocks = []
    for channel in channels:
        feeds = await chat_service.get_chat_feeds(channel_id=channel.channel_id)
        body = _format_feeds(feeds) if feeds else "Нет источников"
        blocks.append(f"<b>📋 {html.escape(channel.title)}</b> ({len(feeds)})\n\n{body}")

    if blocks:
        await message.answer("\n\n".join(blocks), disable_web_page_preview=True)


@commands_router.message(Command("add"))
async def cmd_add(message: Message, command: CommandObject, bot: Bot, db: DB) -> None:
    url = (command.args or "").strip()
    if not url.startswith(("http://", "https://")):
        await message.reply("Использование: /add https://example.com/feed.xml")
        return

    channel = await _resolve_channel(message, bot, db)
    if not channel:
        return

    if await ChatService(db).add_feed_to_chat(channel_id=channel.channel_id, feed_url=url):
        await message.reply(f"✅ Источник добавлен в «{html.escape(channel.title)}»:\n{html.escape(url)}",
                            disable_web_page_preview=True)
    else:
        await message.reply("❌ Не удалось добавить источник. Возможно, он уже добавлен.")


@commands_router.message(Command("remove"))
async def cmd_remove(message: Message, command: CommandObject, bot: Bot, db: DB) -> None:
    arg = (command.args or "").strip()
    if not arg:
        await message.reply("Использование: /remove <номер из /list или url>")
        return

    channel = await _resolve_channel(message, bot, db)
    if not channel:
        return

    chat_service = ChatService(db)
    feeds = await chat_service.get_chat_feeds(channel_id=channel.channel_id)

    if arg.isdigit():
        index = int(arg)
        feed = feeds[index - 1] if 1 <= index <= len(feeds) else None
    else:
        feed = next((f for f in feeds if f.url == arg), None)

    if not feed:
        await message.reply("❌ Источник не найден. Посмотрите номера в /list.")
        return

    if await chat_service.remove_feed_by_id(channel_id=channel.channel_id, feed_id=feed.id):
        await message.reply(f"✅ Источник удалён:\n{html.escape(feed.url)}", disable_web_page_preview=True)
    else:
        await message.reply("❌ Не удалось удалить источник")
