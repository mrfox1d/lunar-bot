from aiogram import Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.filters import CommandStart

from handlers.databases import Database

db = Database()
router = Router()

@router.message(CommandStart())
async def start(message: Message):
    user = await db.get_user(message.from_user.id)
    
    if not user:
        await db.add_user(user_id=message.from_user.id, username=message.from_user.username)

    kb = [
        [InlineKeyboardButton(
            text="🪪 Профиль", 
            callback_data="profile"
        )],
        [InlineKeyboardButton(
            text="📊 Статистика", 
            callback_data="stats"
        )],
        [InlineKeyboardButton(
            text="⚙️ Настройки",
            callback_data="settings"
        )],
        [InlineKeyboardButton(
            text="💎 Премиум", 
            callback_data="premium"
        )],
        [InlineKeyboardButton(
            text="❓ Помощь", 
            callback_data="help"
        )]
        ]
    
    mk = InlineKeyboardMarkup(inline_keyboard=kb)

    if message.chat.type == "private":
        await message.answer(f"🖖 Привет, <b>{message.from_user.first_name}</b>!\n\nВот список действий, доступных к выполнению:", reply_markup=mk, parse_mode="HTML")

    elif message.chat.type in {"group", "supergroup"}:

        reply_message = f"🖖 Привет, <b>{message.from_user.first_name}</b>!\n\nВот список действий, доступных к выполнению:"

        get = await router.get_me()
        username = get.username
        await message.answer(
                f"💬 Сообщение отправлено в <a href='https://t.me/{username}'>ЛС с ботом</a>.", 
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text="Перейти в ЛС", 
                            url=f"https://t.me/{username}"
                        )]
                    ]
                ),
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        await router.send_message(chat_id=message.from_user.id, text=reply_message, reply_markup=mk, parse_mode="HTML")