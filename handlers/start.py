from aiogram import Router, types, F, Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.filters import CommandStart
from handlers.databases import Database

db = Database()
router = Router()

@router.message(CommandStart())
async def start(message: Message, bot: Bot):
    user = await db.get_user(message.from_user.id)
    
    if not user:
        await db.add_user(user_id=message.from_user.id, username=message.from_user.username)

    kb = [
        [
            InlineKeyboardButton(text="🪪 Профиль", callback_data="profile"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")
        ],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton(text="💎 Премиум", callback_data="premium")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ]
    mk = InlineKeyboardMarkup(inline_keyboard=kb)

    welcome_text = (
        f"<b>🖖 Рад встрече, {message.from_user.first_name}!</b>\n\n"
        f"Я твой автоматизированный помощник. Используй меню ниже, "
        f"чтобы управлять своим аккаунтом и просматривать актуальные данные.\n\n"
        f"<i>Выберите нужный раздел:</i>"
    )

    if message.chat.type == "private":
        await message.answer(welcome_text, reply_markup=mk, parse_mode="HTML")

    elif message.chat.type in {"group", "supergroup"}:
        bot_info = await bot.get_me()
        
        await message.reply(
            f"<b>{message.from_user.first_name}</b>, я отправил панель управления тебе в личку! 📥",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(text="Перейти к боту", url=f"https://t.me/{bot_info.username}")
                ]]
            ),
            parse_mode="HTML"
        )

        try:
            await bot.send_message(
                chat_id=message.from_user.id, 
                text=welcome_text, 
                reply_markup=mk, 
                parse_mode="HTML"
            )
        except Exception:
            await message.answer("❌ Не могу отправить сообщение! Пожалуйста, начни диалог со мной в ЛС.")