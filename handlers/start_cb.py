import os
from io import BytesIO
from handlers.databases import Database
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile, InputMediaPhoto
from PIL import ImageDraw, Image, ImageFont

router = Router()
db = Database()

@router.callback_query(F.data == "profile")
async def start_cb(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id

    user = await db.get_user(user_id)
    if not user:
        await db.add_user(user_id, callback.from_user.username)
        user = await db.get_user(user_id)

    avatar_path = f"materials/avatar_{user_id}.jpg"
    photos = await bot.get_user_profile_photos(user_id, limit=1)
    
    if photos.total_count > 0:
        file_id = photos.photos[0][-1].file_id
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, avatar_path)
        avatar = Image.open(avatar_path).resize((383, 383)).convert("RGBA")
    else:
        avatar = Image.new("RGBA", (383, 383), (80, 80, 80, 255))

    base = Image.open("materials/lunar-profile.jpg").convert("RGBA")
    
    mask = Image.new("L", (383, 383), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.rounded_rectangle((0, 0, 383, 383), radius=50, fill=255)
    avatar.putalpha(mask)
    base.paste(avatar, (325, 325), avatar)

    draw = ImageDraw.Draw(base)

    regular = ImageFont.truetype("materials/fonts/MontserratAlternates-Regular.ttf", 45)
    semibold = ImageFont.truetype("materials/fonts/MontserratAlternates-SemiBold.ttf", 125)
    medium = ImageFont.truetype("materials/fonts/MontserratAlternates-Medium.ttf", 100)
    semibold_250 = ImageFont.truetype("materials/fonts/MontserratAlternates-SemiBold.ttf", 250)
    regular_35 = ImageFont.truetype("materials/fonts/MontserratAlternates-Regular.ttf", 35)

    def draw_center(draw, text, center_x, y, font, fill="#FFFFFF"):
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        draw.text((center_x - width / 2, y), text, font=font, fill=fill)

    full_name = callback.from_user.full_name[:18]
    username = f"@{callback.from_user.username}"[:22] if callback.from_user.username else ""
    user_id_text = f"ID: {user_id}"

    draw.text((803, 444), full_name, font=medium, fill="#FFFFFF")
    name_bbox = draw.textbbox((803, 444), full_name, font=medium)
    current_y = name_bbox[3] + 15

    if username:
        draw.text((803, current_y), username, font=regular, fill="#FFFFFF")
        user_bbox = draw.textbbox((803, current_y), username, font=regular)
        current_y = user_bbox[3] + 15
    draw.text((803, current_y), user_id_text, font=regular_35, fill="#888888")

    draw_center(draw, str(user['currency']), 850, 1455, semibold_250)
    
    subscription = await db.get_premium_subscription(user_id)
    is_active = subscription['is_active'] if subscription else False
    icon = Image.open("materials/y.png" if is_active else "materials/n.png").convert("RGBA")
    base.paste(icon, (2181 - icon.width // 2, 1280), icon)

    time_left = await db.get_premium_time_left(user_id)
    days = max(time_left.days, 0) if time_left else 0
    draw_center(draw, f"{days} дн.", 2176, 1821, semibold)

    draw_center(draw, f"{user['daily_ai_requests']}", 3515, 1387, semibold)
    draw_center(draw, f"{user['request_limit']}", 3515, 1821, semibold)

    with BytesIO() as buffer:
        base.convert("RGB").save(buffer, format="JPEG", quality=90)
        buffer.seek(0)
        
        photo_file = BufferedInputFile(buffer.getvalue(), filename=f"profile_{user_id}.jpg")
        media = InputMediaPhoto(media=photo_file)

        kb = [[InlineKeyboardButton(text="🔙 Назад", callback_data="back")]]
        await callback.message.edit_media(media=media, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

    if os.path.exists(avatar_path):
        os.remove(avatar_path)

@router.callback_query(F.data == "back")
async def back_to_main_menu(callback: CallbackQuery):
    kb = [
        [
            InlineKeyboardButton(text="🪪 Профиль", callback_data="profile"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")
        ],
        [InlineKeyboardButton(text="💎 Премиум", callback_data="premium")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ]
    mk = InlineKeyboardMarkup(inline_keyboard=kb)

    welcome_text = (
        f"<b>🖖 Привет, {callback.from_user.first_name}!</b>\n\n"
        f"Вот список действий, доступных к выполнению:"
    )

    await callback.message.delete()

    await callback.message.answer(
        text=welcome_text,
        reply_markup=mk,
        parse_mode="HTML"
    )
    
    await callback.answer()