import json
import random
import sqlite3
import telebot
from telebot import types

TOKEN = "8935480244:AAH3w6vUIkQTnKD9eSCBL8QiwIDKF7NS4kg"
CHANNEL_ID = -1004404647295
ADMIN_CHAT_ID = -1004410094117
ADMIN_IDS = [7959524856]

REQUIRED_TAGS = ['drt', 'd1rty', 'pig.zip']

bot = telebot.TeleBot(TOKEN)

def init_db():
    conn = sqlite3.connect('bot.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users
                   (user_id INTEGER PRIMARY KEY,
                    balance INTEGER DEFAULT 1000,
                    pigs INTEGER DEFAULT 5,
                    is_vip INTEGER DEFAULT 0,
                    passport TEXT DEFAULT '')''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('bot.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cur.fetchone()
    if not user:
        cur.execute("INSERT INTO users (user_id, balance, pigs, passport) VALUES (?, ?, ?, ?)", 
                   (user_id, 1000, 5, ''))
        conn.commit()
        cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        user = cur.fetchone()
    conn.close()
    return user

def update_balance(user_id, amount):
    conn = sqlite3.connect('bot.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def update_pigs(user_id, amount):
    conn = sqlite3.connect('bot.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET pigs = pigs + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def set_passport(user_id, passport_data):
    conn = sqlite3.connect('bot.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET passport = ? WHERE user_id=?", (json.dumps(passport_data), user_id))
    conn.commit()
    conn.close()

def get_passport(user_id):
    user = get_user(user_id)
    if user[4]:
        return json.loads(user[4])
    return {}

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add('🎰 Казино', '💳 Баланс', '📋 Паспорт')
    markup.add('🐷 Свиньи', '⭐ Купить VIP за звезды', '📤 Предложить слив')
    return markup

def get_casino_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add('🎲 Кости', '🎰 Слоты')
    markup.add('💣 Мины', '🔙 Назад')
    return markup

def get_shop_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add('🐷 Купить свинью (500💰)', '💎 Продать свинью (300💰)')
    markup.add('🔙 Назад')
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    get_user(message.from_user.id)
    bot.send_message(message.chat.id, "🎰 <b>Добро пожаловать в игровой мир!</b>\nИспользуй кнопки ниже:", parse_mode='HTML', reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda m: m.text == '🔙 Назад')
def back_to_main(message):
    bot.send_message(message.chat.id, "Главное меню:", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda m: m.text == '💳 Баланс')
def balance_menu(message):
    user = get_user(message.from_user.id)
    vip = "👑 Да" if user[3] else "❌ Нет"
    bot.send_message(message.chat.id, f"💳 <b>Твой профиль:</b>\n💰 Баланс: <code>{user[1]}</code> монет\n🐷 Свиней: <code>{user[2]}</code>\n👑 VIP статус: <code>{vip}</code>", parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text == '🎰 Казино')
def casino_menu(message):
    bot.send_message(message.chat.id, "🎰 <b>Раздел казино:</b> Выбирай игру:", parse_mode='HTML', reply_markup=get_casino_keyboard())

@bot.message_handler(func=lambda m: m.text == '🎲 Кости')
def dice_game(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    bet = 50
    if user[1] < bet:
        bot.send_message(message.chat.id, "❌ Недостаточно монет!")
        return
    update_balance(user_id, -bet)
    res = random.randint(1, 6)
    if res >= 4:
        win = bet * 2
        update_balance(user_id, win)
        bot.send_message(message.chat.id, f"🎲 Выпало: {res}\n🎉 Победа! +{win} монет!")
    else:
        bot.send_message(message.chat.id, f"🎲 Выпало: {res}\n😢 Проигрыш! -{bet} монет")

@bot.message_handler(func=lambda m: m.text == '🎰 Слоты')
def slots_game(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    bet = 100
    if user[1] < bet:
        bot.send_message(message.chat.id, "❌ Недостаточно монет!")
        return
    update_balance(user_id, -bet)
    symbols = ['🍒', '🍋', '7️⃣', '💎']
    res = [random.choice(symbols) for _ in range(3)]
    if res[0] == res[1] == res[2]:
        win = bet * 5
        update_balance(user_id, win)
        text = f"🎰 {' '.join(res)}\n🎉 ДЖЕКПОТ! +{win} монет!"
    elif res[0] == res[1] or res[1] == res[2]:
        win = bet * 2
        update_balance(user_id, win)
        text = f"🎰 {' '.join(res)}\n🎉 Выигрыш! +{win} монет!"
    else:
        text = f"🎰 {' '.join(res)}\n😢 Проигрыш -{bet} монет"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == '💣 Мины')
def mines_game(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    bet = 200
    if user[1] < bet:
        bot.send_message(message.chat.id, "❌ Недостаточно монет!")
        return
    update_balance(user_id, -bet)
    markup = types.InlineKeyboardMarkup(row_width=3)
    for i in range(1, 10):
        markup.add(types.InlineKeyboardButton(f"📦 Клетка {i}", callback_data=f"mine_{i}_{bet}"))
    bot.send_message(message.chat.id, f"💣 <b>Мины (Квадрат 3x3)</b>\nСтавка: {bet} монет.\nВыбери безопасную ячейку:", parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('mine_'))
def mine_callback(call):
    _, cell, bet = call.data.split('_')
    bet = int(bet)
    win = random.choice([True, False])
    if win:
        reward = bet * 2
        update_balance(call.from_user.id, reward)
        bot.edit_message_text(f"💣 Клетка #{cell}\n💎 АЛМАЗ! +{reward} монет!", call.message.chat.id, call.message.message_id)
    else:
        bot.edit_message_text(f"💣 Клетка #{cell}\n💥 БУХ! Ты подорвался на мине!", call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: m.text == '📋 Паспорт')
def passport_menu(message):
    user_id = message.from_user.id
    passport = get_passport(user_id)
    if not passport:
        passport = {'name': message.from_user.first_name, 'tags': ['drt']}
        set_passport(user_id, passport)
    tags = passport.get('tags', [])
    has_tag = any(t in tags for t in REQUIRED_TAGS)
    status = "✅ Проверен" if has_tag else "❌ Нет приписки"
    text = f"""
📋 <b>ЛИЧНЫЙ ПАСПОРТ ИГРОКА</b>
━━━━━━━━━━━━━━━━━━━━━
🆔 ID: <code>{user_id}</code>
👤 Имя: <code>{passport.get('name')}</code>
🏷️ Приписки: <code>{', '.join(tags)}</code>
📌 Статус: <code>{status}</code>
━━━━━━━━━━━━━━━━━━━━━
"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🏷️ Добавить приписку", callback_data="add_tag_menu"))
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "add_tag_menu")
def add_tag_prompt(call):
    markup = types.InlineKeyboardMarkup()
    for tag in REQUIRED_TAGS:
        markup.add(types.InlineKeyboardButton(f"+ {tag}", callback_data=f"apply_tag_{tag}"))
    bot.edit_message_text("Выбери приписку для добавления в паспорт:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('apply_tag_'))
def apply_tag(call):
    tag = call.data.split('_')[2]
    user_id = call.from_user.id
    passport = get_passport(user_id)
    tags = passport.get('tags', [])
    if tag not in tags:
        tags.append(tag)
        passport['tags'] = tags
        set_passport(user_id, passport)
    bot.answer_callback_query(call.id, f"Успешно добавлена приписка: {tag}!", show_alert=True)
    bot.edit_message_text(f"✅ Приписка <b>{tag}</b> добавлена в твой паспорт!", call.message.chat.id, call.message.message_id, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text == '🐷 Свиньи')
def pigs_shop(message):
    user = get_user(message.from_user.id)
    bot.send_message(message.chat.id, f"🐷 <b>Ферма свиней</b>\nУ тебя свиней: <code>{user[2]}</code>\nБаланс: <code>{user[1]}</code> монет\n", parse_mode='HTML', reply_markup=get_shop_keyboard())

@bot.message_handler(func=lambda m: m.text == '🐷 Купить свинью (500💰)')
def buy_pig(message):
    user = get_user(message.from_user.id)
    if user[1] < 500:
        bot.send_message(message.chat.id, "❌ Недостаточно монет для покупки свиньи!")
        return
    update_balance(message.from_user.id, -500)
    update_pigs(message.from_user.id, 1)
    bot.send_message(message.chat.id, "🐷 Ты успешно купил свинью!")

@bot.message_handler(func=lambda m: m.text == '💎 Продать свинью (300💰)')
def sell_pig(message):
    user = get_user(message.from_user.id)
    if user[2] < 1:
        bot.send_message(message.chat.id, "❌ У тебя нет свиней для продажи!")
        return
    update_pigs(message.from_user.id, -1)
    update_balance(message.from_user.id, 300)
    bot.send_message(message.chat.id, "💎 Ты продал свинью за 300 монет!")

@bot.message_handler(func=lambda m: m.text == '⭐ Купить VIP за звезды')
def buy_vip_stars(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⭐ Оплатить 25 Telegram Stars", callback_data="pay_vip_stars"))
    bot.send_message(message.chat.id, "👑 <b>Покупка VIP-статуса</b>\nСтоимость: <b>25 ⭐</b>", parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "pay_vip_stars")
def process_star_payment(call):
    prices = [types.LabeledPrice(label="VIP статус", amount=25)]
    bot.send_invoice(
        chat_id=call.message.chat.id,
        title="👑 VIP Статус",
        description="Премиум-статус в боте",
        invoice_payload="vip_stars",
        provider_token="",
        currency="XTR",
        prices=prices
    )
    bot.answer_callback_query(call.id)

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    conn = sqlite3.connect('bot.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_vip = 1 WHERE user_id=?", (message.from_user.id,))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "🎉 <b>Оплата прошла успешно! Тебе выдан VIP-статус!</b>", parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text == '📤 Предложить слив')
def propose_slip(message):
    bot.send_message(message.chat.id, "📤 Отправь следующим сообщением контент (текст, фото, видео) для модерации.")
    bot.register_next_step_handler(message, forward_to_admin)

def forward_to_admin(message):
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Подтвердить и слить в канал", callback_data=f"publish_{user_id}"))
    sent = bot.forward_message(ADMIN_CHAT_ID, message.chat.id, message.message_id)
    bot.send_message(ADMIN_CHAT_ID, f"📥 Предложка от <code>{user_id}</code>:", parse_mode='HTML', reply_markup=markup, reply_to_message_id=sent.message_id)
    bot.send_message(message.chat.id, "✅ Отправлено администратору на проверку!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('publish_'))
def publish_slip(call):
    try:
        bot.copy_message(CHANNEL_ID, call.message.chat.id, call.message.reply_to_message.message_id)
        bot.edit_message_text("✅ Успешно опубликовано в канал!", call.message.chat.id, call.message.message_id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"Ошибка: {e}", show_alert=True)
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ Накрутить монеты по ID", callback_data="adm_add_coins"))
    markup.add(types.InlineKeyboardButton("🐷 Накрутить свиней по ID", callback_data="adm_add_pigs"))
    bot.send_message(message.chat.id, "👑 <b>Панель администратора:</b>\nВыбери действие:", parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["adm_add_coins", "adm_add_pigs"])
def adm_action_step(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    action = call.data
    msg = bot.send_message(call.message.chat.id, "✍️ Введи ID игрока и количество через пробел:\n<i>Пример:</i> <code>7959524856 10000</code>", parse_mode='HTML')
    if action == "adm_add_coins":
        bot.register_next_step_handler(msg, process_add_coins)
    else:
        bot.register_next_step_handler(msg, process_add_pigs)
    bot.answer_callback_query(call.id)

def process_add_coins(message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        args = message.text.split()
        target_id, amount = int(args[0]), int(args[1])
        update_balance(target_id, amount)
        bot.send_message(message.chat.id, f"✅ Успешно начислено {amount} монет игроку <code>{target_id}</code>!", parse_mode='HTML')
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

def process_add_pigs(message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        args = message.text.split()
        target_id, amount = int(args[0]), int(args[1])
        update_pigs(target_id, amount)
        bot.send_message(message.chat.id, f"✅ Успешно добавлено {amount} свиней игроку <code>{target_id}</code>!", parse_mode='HTML')
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

if __name__ == "__main__":
    init_db()
    print("Бот полностью запущен и готов к работе!")
    bot.infinity_polling()

