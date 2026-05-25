import asyncio
import os
import re
import json
from io import BytesIO
from PIL import Image, ImageOps, ImageDraw, ImageFont
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ===== НАСТРОЙКИ =====
TOKEN = "8551596963:AAFabdYFc_zCrA5cDh2_U5Va1TWPtmVcBeQ"
PROXY_URL = "socks5://GXjt8nK3:ghhPdd4C@153.80.158.91:64773"

TEMPLATE_PATH = "template.jpg" 
FONT_PATH = "fonts/Montserrat-Bold.ttf" 

TARGET_WIDTH = 204         
TARGET_HEIGHT = 864        
PASTE_X = 83               
PASTE_Y = 193              
CORNER_RADIUS = 25 

# Координаты зон
TEXT_COORDS = (434, 482)
TEXT_AREA_WIDTH = 110; TEXT_AREA_HEIGHT = 66; FONT_SIZE = 36 
SECOND_TEXT_COORDS = (305, 904); SECOND_AREA_WIDTH = 165; SECOND_AREA_HEIGHT = 23; SECOND_FONT_SIZE = 16
THIRD_TEXT_COORDS = (399, 270); THIRD_AREA_WIDTH = 189; THIRD_AREA_HEIGHT = 22; THIRD_FONT_SIZE = 14
FOURTH_TEXT_COORDS = (448, 416); FOURTH_AREA_WIDTH = 87; FOURTH_AREA_HEIGHT = 28; FOURTH_FONT_SIZE = 18
FIFTH_TEXT_COORDS = (325, 763); FIFTH_AREA_WIDTH = 25; FIFTH_AREA_HEIGHT = 12; FIFTH_FONT_SIZE = 10

# ===== НАСТРОЙКИ АДМИНКИ =====
ADMIN_PASSWORD = "dobodobo656"
USERS_FILE = "users.json"
BANNED_FILE = "banned.json"
ADMINS = set() # ID авторизованных админов в текущей сессии

def load_set(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return set(json.load(f))
    return set()

def save_set(filename, data_set):
    with open(filename, 'w') as f:
        json.dump(list(data_set), f)

all_users = load_set(USERS_FILE)
banned_users = load_set(BANNED_FILE)


# --- ФУНКЦИИ ФОРМАТИРОВАНИЯ И РИСОВАНИЯ ---
def format_phone(raw_phone):
    digits = "".join([c for c in raw_phone if c.isdigit()])
    digits = digits[:11]
    if len(digits) == 11:
        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    elif len(digits) == 10:
        return f"+7 ({digits[0:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:10]}"
    return raw_phone

def format_datetime(raw_text):
    months = {
        1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня", 
        7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
    }
    match = re.search(r"(\d{1,2})[\./-](\d{1,2})[\./-](\d{2,4})[^\d]+(\d{1,2})[:\.](\d{2})", raw_text)
    if match:
        day, month, year, hour, minute = map(int, match.groups())
        if year < 100: year += 2000
        if 1 <= month <= 12:
            return f"{day} {months[month]} {year} • {hour:02d}:{minute:02d}"
    return raw_text

def clean_iphone_screen(image_bytes):
    img = Image.open(image_bytes).convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size
    draw.rectangle((0, 0, w, int(h * 0.055)), fill=(0, 0, 0))
    draw.rectangle((int(w * 0.2), int(h * 0.975), int(w * 0.8), h), fill=(0, 0, 0))
    return img

def process_and_paste(user_screenshot_bytes, text_value, phone_value, datetime_value, name_value, card_value):
    template = Image.open(TEMPLATE_PATH).convert("RGBA")
    user_img = Image.open(user_screenshot_bytes).convert("RGBA")
    user_img_cropped = ImageOps.fit(user_img, (TARGET_WIDTH, TARGET_HEIGHT), method=Image.Resampling.LANCZOS, centering=(0.0, 0.5))
    
    mask = Image.new('L', (TARGET_WIDTH, TARGET_HEIGHT), 0) 
    draw = ImageDraw.Draw(mask)
    r = CORNER_RADIUS
    draw.rectangle((0, r, TARGET_WIDTH, TARGET_HEIGHT - r), fill=255)
    draw.rectangle((r, 0, TARGET_WIDTH, TARGET_HEIGHT), fill=255)
    draw.ellipse([(0, 0), (r * 2, r * 2)], fill=255)
    draw.ellipse([(0, TARGET_HEIGHT - r * 2), (r * 2, TARGET_HEIGHT)], fill=255)
    
    template.paste(user_img_cropped, (int(PASTE_X), int(PASTE_Y)), mask=mask)
    draw_text = ImageDraw.Draw(template)
    
    font_main = font_phone = font_datetime = font_name = font_card = ImageFont.load_default()
    if os.path.exists(FONT_PATH):
        font_main = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        font_phone = ImageFont.truetype(FONT_PATH, SECOND_FONT_SIZE)
        font_datetime = ImageFont.truetype(FONT_PATH, THIRD_FONT_SIZE) 
        font_name = ImageFont.truetype(FONT_PATH, FOURTH_FONT_SIZE)
        font_card = ImageFont.truetype(FONT_PATH, FIFTH_FONT_SIZE)
        
    def draw_centered_text(bbox_coords, text, font, area_w, area_h):
        bbox = draw_text.textbbox((0, 0), text, font=font)
        x = bbox_coords[0] + (area_w - (bbox[2] - bbox[0])) // 2
        y = bbox_coords[1] + (area_h - (bbox[3] - bbox[1])) // 2
        draw_text.text((x, y), text, font=font, fill=(255, 255, 255, 255))

    draw_centered_text(TEXT_COORDS, text_value, font_main, TEXT_AREA_WIDTH, TEXT_AREA_HEIGHT)
    draw_centered_text(SECOND_TEXT_COORDS, phone_value, font_phone, SECOND_AREA_WIDTH, SECOND_AREA_HEIGHT)
    draw_centered_text(THIRD_TEXT_COORDS, datetime_value, font_datetime, THIRD_AREA_WIDTH, THIRD_AREA_HEIGHT)
    draw_centered_text(FOURTH_TEXT_COORDS, name_value, font_name, FOURTH_AREA_WIDTH, FOURTH_AREA_HEIGHT)
    draw_centered_text(FIFTH_TEXT_COORDS, card_value, font_card, FIFTH_AREA_WIDTH, FIFTH_AREA_HEIGHT)
    
    return template.convert("RGB")


# --- ПРОВЕРКА ПОЛЬЗОВАТЕЛЯ ---
def check_user(user_id):
    """Возвращает True если юзер забанен, иначе False.
    Заодно сохраняет новых юзеров."""
    if user_id in banned_users:
        return True
    if user_id not in all_users:
        all_users.add(user_id)
        save_set(USERS_FILE, all_users)
    return False


# --- ЛОГИКА БОТА ---
def init_user_data(user_data):
    if 'sum' not in user_data: user_data['sum'] = "-450 ₽"
    if 'phone' not in user_data: user_data['phone'] = "+7 (999) 000-00-00"
    if 'name' not in user_data: user_data['name'] = "Иван И."
    if 'date' not in user_data: user_data['date'] = "1 сентября 2025 • 14:32"
    if 'card' not in user_data: user_data['card'] = "1234"
    if 'crop' not in user_data: user_data['crop'] = False
    if 'awaiting' not in user_data: user_data['awaiting'] = None

def get_draw_menu(user_data):
    crop_status = "✅ Вкл" if user_data.get('crop') else "❌ Выкл"
    keyboard = [
        [InlineKeyboardButton(f"💵 Сумма: {user_data.get('sum')}", callback_data="set_sum")],
        [InlineKeyboardButton(f"📱 Номер: {user_data.get('phone')}", callback_data="set_phone")],
        [InlineKeyboardButton(f"👤 Имя: {user_data.get('name')}", callback_data="set_name")],
        [InlineKeyboardButton(f"📅 Дата: {user_data.get('date')}", callback_data="set_date")],
        [InlineKeyboardButton(f"💳 Карта: {user_data.get('card')}", callback_data="set_card")],
        [InlineKeyboardButton(f"✂️ скрыть статус бар: {crop_status}", callback_data="toggle_crop")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def show_admin_menu(update: Update):
    keyboard = [
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🚫 Заблокировать", callback_data="admin_ban"),
         InlineKeyboardButton("🔓 Разблокировать", callback_data="admin_unban")]
    ]
    msg = f"⚙️ **Панель администратора**\nВсего пользователей: {len(all_users)}\nЗаблокировано: {len(banned_users)}"
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if check_user(user_id): return
    
    if user_id in ADMINS:
        context.user_data['awaiting'] = None
        await show_admin_menu(update)
    else:
        context.user_data['awaiting'] = 'admin_password'
        await update.message.reply_text("🔐 Введите код доступа:")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if check_user(update.effective_user.id): return
    init_user_data(context.user_data)
    keyboard = [
        [InlineKeyboardButton("🎨 Рисовать", callback_data="draw")],
        [InlineKeyboardButton("📢 Наш канал", url="https://t.me/AfinaDraft")]
    ]
    await update.message.reply_text("Добро пожаловать в Afina Draft ⚡️\n┗ Меню ниже ⬇️", reply_markup=InlineKeyboardMarkup(keyboard))


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if check_user(user_id): return
    await query.answer()
    
    user_data = context.user_data
    init_user_data(user_data)

    # Логика обычного юзера
    if query.data == "draw":
        user_data['awaiting'] = None
        msg = "🕹️ Здесь укажи свои данные, после просто отправь скриншот со сделкой.\n\n🔺Примечание: Всегда нажимайте « Скрыть статус бар » для корректной рисовки"
        await query.edit_message_text(msg, reply_markup=get_draw_menu(user_data), parse_mode="Markdown")

    elif query.data in ["set_sum", "set_phone", "set_name", "set_date", "set_card"]:
        user_data['awaiting'] = query.data
        prompts = {
            "set_sum": "Введите  сумму (например: -500):",
            "set_phone": "Введите номер телефона:",
            "set_name": "Введите Имя и Фамилию:",
            "set_date": "Введите дату и время (например: 01.01.26 12:00):",
            "set_card": "Последние 4 цифры карты отправителя:"
        }
        await query.edit_message_text(prompts[query.data], reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="draw")]]))

    elif query.data == "toggle_crop":
        user_data['crop'] = not user_data['crop']
        msg = "🕹️ Здесь укажи свои данные, после просто отправь скриншот со сделкой.\n\n🔺Примечание: Всегда нажимайте « Скрыть статус бар » для корректной рисовки"
        await query.edit_message_text(msg, reply_markup=get_draw_menu(user_data), parse_mode="Markdown")

    # Логика админа
    elif query.data == "admin_broadcast":
        user_data['awaiting'] = 'admin_broadcast'
        await query.edit_message_text("Отправьте сообщение (текст или фото) для рассылки всем пользователям:")
        
    elif query.data == "admin_ban":
        user_data['awaiting'] = 'admin_ban'
        await query.edit_message_text("Введите Telegram ID пользователя для БЛОКИРОВКИ:")
        
    elif query.data == "admin_unban":
        user_data['awaiting'] = 'admin_unban'
        await query.edit_message_text("Введите Telegram ID пользователя для РАЗБЛОКИРОВКИ:")


async def execute_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Универсальная функция рассылки для текста и фото"""
    await update.message.reply_text("⏳ Начинаю рассылку...")
    success = 0
    for uid in all_users:
        if uid in banned_users: continue
        try:
            await context.bot.copy_message(chat_id=uid, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
            success += 1
        except Exception:
            pass
    context.user_data['awaiting'] = None
    await update.message.reply_text(f"✅ Рассылка завершена!\nДоставлено: {success} пользователям.")
    await show_admin_menu(update)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if check_user(user_id): return
    user_data = context.user_data
    init_user_data(user_data)
    awaiting = user_data.get('awaiting')
    if not awaiting: return 

    text = update.message.text
    
    # === АДМИН-ОБРАБОТЧИКИ ===
    if awaiting == 'admin_password':
        if text == ADMIN_PASSWORD:
            ADMINS.add(user_id)
            user_data['awaiting'] = None
            await show_admin_menu(update)
        else:
            user_data['awaiting'] = None
            await update.message.reply_text("❌ Неверный пароль.")
        return

    elif awaiting == 'admin_broadcast':
        await execute_broadcast(update, context)
        return

    elif awaiting == 'admin_ban':
        try:
            target_id = int(text)
            banned_users.add(target_id)
            save_set(BANNED_FILE, banned_users)
            await update.message.reply_text(f"✅ ID {target_id} заблокирован.")
        except ValueError:
            await update.message.reply_text("❌ Введите корректный числовой ID.")
        user_data['awaiting'] = None
        await show_admin_menu(update)
        return

    elif awaiting == 'admin_unban':
        try:
            target_id = int(text)
            if target_id in banned_users:
                banned_users.remove(target_id)
                save_set(BANNED_FILE, banned_users)
                await update.message.reply_text(f"✅ ID {target_id} разблокирован.")
            else:
                await update.message.reply_text("Этот ID не заблокирован.")
        except ValueError:
            await update.message.reply_text("❌ Введите корректный числовой ID.")
        user_data['awaiting'] = None
        await show_admin_menu(update)
        return

    # === ПОЛЬЗОВАТЕЛЬСКИЕ ОБРАБОТЧИКИ ===
    if awaiting == "set_sum":
        clean = text.replace("₽", "").replace(" ", "").strip()
        try:
            user_data['sum'] = f"{int(clean):,}".replace(",", " ") + " ₽"
        except ValueError:
            user_data['sum'] = text if text.endswith("₽") else text + " ₽"
    elif awaiting == "set_phone": user_data['phone'] = format_phone(text)
    elif awaiting == "set_name": user_data['name'] = text
    elif awaiting == "set_date": user_data['date'] = format_datetime(text)
    elif awaiting == "set_card": 
        digits = "".join([c for c in text if c.isdigit()])
        user_data['card'] = digits[:4] if digits else text[:4]

    user_data['awaiting'] = None
    await update.message.reply_text("✅ Данные сохранены!\n\nЖду скриншот или изменения других параметров:", reply_markup=get_draw_menu(user_data))


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if check_user(user_id): return
    user_data = context.user_data
    init_user_data(user_data)
    
    # Если админ отправляет фото для рассылки
    if user_data.get('awaiting') == 'admin_broadcast':
        await execute_broadcast(update, context)
        return

    # Логика генерации чека
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = BytesIO()
    await photo_file.download_to_memory(photo_bytes)
    photo_bytes.seek(0)
    
    if user_data.get('crop'):
        cleaned_img = clean_iphone_screen(photo_bytes)
        photo_bytes = BytesIO()
        cleaned_img.save(photo_bytes, format="PNG") 
        photo_bytes.seek(0)

    result_img = process_and_paste(
        photo_bytes, user_data['sum'], user_data['phone'], 
        user_data['date'], user_data['name'], user_data['card']
    )
    result_bytes = BytesIO()
    result_img.save(result_bytes, format="JPEG", quality=100, subsampling=0)
    result_bytes.seek(0)
    
    await update.message.reply_document(document=result_bytes, filename="ready_bill.jpg")


async def main():
    application = Application.builder().token(TOKEN).proxy_url(PROXY_URL).get_updates_proxy_url(PROXY_URL).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", cmd_admin))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("Бот запущен. Ожидание сообщений...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await asyncio.Event().wait()


if __name__ == '__main__':
    try: 
        asyncio.run(main())
    except KeyboardInterrupt: 
        pass
