from aiogram import types, Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ChatMemberUpdated
import handlers.mod as db

router = Router()

@router.my_chat_member()
async def bot_added_to_group(update: ChatMemberUpdated):
    if update.new_chat_member.status == "member":
        chat = update.chat
        
        if chat.type in ["group", "supergroup"]:
            try:
                admins = await update.bot.get_chat_administrators(chat.id)
                
                # Ищем создателя группы
                for admin in admins:
                    if admin.status == "creator":
                        actual_owner_id = admin.user.id
                        break
                
                # Если овнер не найден, используем того, кто добавил
                if not actual_owner_id:
                    actual_owner_id = inviter.id

            except Exception as e:
                print(f"❌ Ошибка при получении администраторов: {e}")
                actual_owner_id = inviter.id
            
            # Создаем запись о группе в БД
            await add_group_to_db(
                group_id=chat.id,
                owner_id=actual_owner_id,
                title=chat.title
            )
            
            await setup_default_ranks(chat.id)
            
            if inviter.id != actual_owner_id:
                rank = 4 if chat_member.status == "administrator" else 1
                await add_member_to_group(
                    group_id=chat.id,
                    user_id=inviter.id,
                    rank_priority=rank
                )
            
            await update.bot.send_message(
                chat_id=chat.id,
                text=f"🌙 **Привет! Я Lunár** — ваш умный помощник для модерации и развлечений!\n\n"
                     f"✨ Я включен в группу **{chat.title}**\n\n"
                     f"🎯 **Мои функции:**\n"
                     f"🛡️ **Модерация** — бан, кик, мьют, варны\n"
                     f"🤖 **ИИ** — спросить что-то, генерировать текст\n"
                     f"🎮 **Развлечения** — игры, викторины, реакции\n\n"
                     f"👑 Создатель: <a href='tg://user/{actual_owner_id}'>ID {actual_owner_id}</a>"
            )
    
    elif update.new_chat_member.status == KICKED:
        await remove_group_from_db(chat_id=update.chat.id)