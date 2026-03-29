from handlers.databases import Database
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile, InputMediaPhoto
from PIL import ImageDraw, Image, ImageFont

router = Router()
db = Database()

@router.callback_query(F.data == "profile")
async def start_cb(callback: CallbackQuery):
    user_id = callback.message.from_user.id

    # --- получаем юзера ---
    user = await db.get_user(user_id)

    # --- скачиваем аватар ---
    file = await callback.bot.get_file(callback.message.from_user.photo[-1].file_id)
    avatar_path = f"materials/avatar_{user_id}.jpg"
    await callback.bot.download_file(file.file_path, avatar_path)

    # --- база ---
    base = Image.open("materials/lunar-profile.jpg").convert("RGBA")
    avatar = Image.open(avatar_path).resize((383, 383)).convert("RGBA")

    # --- скругление ---
    mask = Image.new("L", (383, 383), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.rounded_rectangle((0, 0, 383, 383), radius=50, fill=255)
    avatar.putalpha(mask)

    base.paste(avatar, (325, 325), avatar)

    draw = ImageDraw.Draw(base)

    # --- шрифты ---
    regular = ImageFont.truetype("materials/fonts/MontserratAlternates-Regular.ttf", 45)
    semibold = ImageFont.truetype("materials/fonts/MontserratAlternates-SemiBold.ttf", 125)
    medium = ImageFont.truetype("materials/fonts/MontserratAlternates-Medium.ttf", 100)
    semibold_250 = ImageFont.truetype("materials/fonts/MontserratAlternates-SemiBold.ttf", 250)
    regular_35 = ImageFont.truetype("materials/fonts/MontserratAlternates-Regular.ttf", 35)

    # --- универсальная функция центрирования ---
    def draw_center(draw, text, center_x, y, font, fill="#FFFFFF"):
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        draw.text((center_x - width / 2, y), text, font=font, fill=fill)

    # --- имя ---
    full_name = callback.message.from_user.full_name[:18]
    username = f"@{callback.message.from_user.username}"[:22] if callback.message.from_user.username else ""
    user_id_text = f"ID: {user_id}"

    start_x = 803
    start_y = 444
    spacing = 15

    draw.text((start_x, start_y), full_name, font=medium, fill="#FFFFFF")

    name_h = draw.textbbox((start_x, start_y), full_name, font=medium)[3]
    current_y = name_h + spacing

    if username:
        draw.text((start_x, current_y), username, font=regular, fill="#FFFFFF")
        current_y += draw.textbbox((start_x, current_y), username, font=regular)[3] + spacing

    draw.text((start_x, current_y), user_id_text, font=regular_35, fill="#888888")

    # --- баланс ---
    balance = user["currency"]
    display_balance = "999999+" if len(str(balance)) > 6 else str(balance)

    draw_center(draw, display_balance, 545, 1455, semibold_250)

    # --- премиум ---
    subscription = await db.get_premium_subscription(user_id)
    is_active = subscription["is_active"] if subscription else False

    check_icon = Image.open("materials/y.png").convert("RGBA")
    cross_icon = Image.open("materials/n.png").convert("RGBA")
    icon = check_icon if is_active else cross_icon

    base.paste(icon, (2051 - icon.width // 2, 1280), icon)

    # --- дни премиума ---
    time_left = await db.get_premium_time_left(user_id)
    days = max(time_left.days, 0) if time_left else 0
    draw_center(draw, f"{days} дн.", 1916, 1821, semibold)

    # --- лимиты ---
    spent = user["daily_ai_requests"]
    limit = user["request_limit"]

    draw_center(draw, f"{spent} запросов", 3115, 1387, semibold)
    draw_center(draw, f"{limit} запросов", 3105, 1821, semibold)

    # --- сохраняем ---
    result_path = f"materials/ready_profile_{user_id}.jpg"
    base.convert("RGB").save(result_path, "JPEG", quality=95)

    # --- клавиатура ---
    kb = [[InlineKeyboardButton(text="🔙 Назад", callback_data="back")]]
    markup = InlineKeyboardMarkup(inline_keyboard=kb)

    # --- редактируем сообщение ---
    media = InputMediaPhoto(media=FSInputFile(result_path))

    await callback.message.edit_media(media=media, reply_markup=markup)