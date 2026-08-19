import asyncio
from datetime import datetime, timedelta
import random
import sqlite3
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
)

# ТВОИ ДАННЫЕ
TOKEN = "8983343344:AAFk61fK5vLB7yn1k9OP0MtTAbenRyobBcI"
ADMIN_ID = 7959524856
ADMIN_USERNAME = "depressedrussiankid"  # Твой точный юзернейм для связи

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# БАЗА ДАННЫХ
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 100,
    vip_expires TEXT,
    last_daily TEXT,
    invited_by INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS promos (
    code TEXT PRIMARY KEY,
    reward INTEGER
)
""")
conn.commit()


# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
def get_user_data(user_id):
  cursor.execute(
      "SELECT balance, vip_expires, last_daily FROM users WHERE user_id = ?",
      (user_id,),
  )
  data = cursor.fetchone()
  if not data:
    cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    return 100, None, None
  return data[0], data[1], data[2]


def is_vip(vip_expires):
  if not vip_expires:
    return False
  return datetime.now() < datetime.fromisoformat(vip_expires)


# ЗАЩИТА: Бот автоматически выходит из группы, если его добавил не ты
@router.my_chat_member()
async def bot_added_to_chat(event):
  if event.new_chat_member.status in ["member", "administrator"]:
    if event.from_user.id != ADMIN_ID:
      await bot.send_message(
          event.chat.id,
          "❌ Йоу, этот бот приватный и принадлежит моему создателю!",
      )
      await bot.leave_chat(event.chat.id)


# --- ГЛАВНОЕ МЕНЮ ДЛЯ ЛИЧНЫХ СООБЩЕНИЙ С КНОПКАМИ ---
def get_main_keyboard():
  return InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="🪪 Профиль / Паспорт", callback_data="menu_profile"
              ),
              InlineKeyboardButton(
                  text="🪙 Баланс", callback_data="menu_balance"
              ),
          ],
          [
              InlineKeyboardButton(
                  text="🎰 Игры и Казино", callback_data="menu_games"
              ),
              InlineKeyboardButton(text="🏆 Топ", callback_data="menu_top"),
          ],
          [
              InlineKeyboardButton(
                  text="🎁 Ежедневка", callback_data="menu_daily"
              ),
              InlineKeyboardButton(
                  text="⭐ Купить VIP / Монеты", callback_data="menu_shop"
              ),
          ],
          [
              InlineKeyboardButton(
                  text="🔗 Рефералка", callback_data="menu_ref"
              ),
              InlineKeyboardButton(
                  text="💬 Связь с админом", url=f"https://t.me/{ADMIN_USERNAME}"
              ),
          ],
      ]
  )


@router.message(Command("start"))
async def cmd_start(message: Message):
  args = message.text.split()
  user_id = message.from_user.id
  get_user_data(user_id)

  # Обработка рефералки в ЛС
  if len(args) > 1 and args[1].startswith("ref_"):
    ref_id = int(args[1].split("_")[1])
    if ref_id != user_id:
      cursor.execute(
          "SELECT invited_by FROM users WHERE user_id = ?", (user_id,)
      )
      res = cursor.fetchone()
      if res and not res[0]:
        cursor.execute(
            "UPDATE users SET invited_by = ? WHERE user_id = ?",
            (ref_id, user_id),
        )
        cursor.execute(
            "UPDATE users SET balance = balance + 50 WHERE user_id = ?",
            (ref_id,),
        )
        cursor.execute(
            "UPDATE users SET balance = balance + 50 WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()
        await message.answer(
            "🔥 Залетел по рефералке! Лови бонус +50 монет на счёт 🪙"
        )

  text = (
      "👋 Здарова! Добро пожаловать в наш бот.\nЖми на кнопки ниже или юзай"
      " команды в чате!"
  )

  if message.chat.type == "private":
    await message.answer(text, reply_markup=get_main_keyboard())
  else:
    await message.answer(
        "Йоу! Бот на связи. Основное меню ждет тебя в личных сообщениях! 🔥"
    )


# --- ОБРАБОТЧИК КНОПОК ИЗ ЛС ---
@router.callback_query(F.data.startswith("menu_"))
async def callback_handler(callback: CallbackQuery):
  action = callback.data.split("_")[1]
  user_id = callback.from_user.id
  bal, vip_exp, last_daily = get_user_data(user_id)

  back_kb = InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="menu_back")]
      ]
  )

  if action == "profile":
    status = "👑 Элитный (Активен)" if is_vip(vip_exp) else "❌ Обычный"
    text = (
        f"🪪 **Твой Паспорт:**\n\n🆔 ID: `{user_id}`\n🪙 Баланс:"
        f" `{bal}`\n⭐ VIP-статус: {status}"
    )
    await callback.message.edit_text(text, reply_markup=back_kb, parse_mode="Markdown")

  elif action == "balance":
    await callback.message.edit_text(
        f"🪙 Твой текущий баланс: `{bal}` монет. Неплохо, но можно и больше! 😎",
        reply_markup=back_kb,
        parse_mode="Markdown",
    )

  elif action == "games":
    text = (
        "🎰 **Казино и Игры:**\n\nМожешь играть прямо в чатах с помощью"
        " команд:\n• `/slots <ставка>` — Слоты\n• `/dice <ставка>` —"
        " Кубик\n• `/mines <ставка>` — Мины\n\n⚡️ Минимальная ставка: `5` монет"
        " (VIP дает x2 к выигрышу и +15% удачи в минах!)"
    )
    await callback.message.edit_text(
        text, reply_markup=back_kb, parse_mode="Markdown"
    )

  elif action == "top":
    cursor.execute(
        "SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10"
    )
    top_users = cursor.fetchall()
    text = "🏆 **Топ-10 богатеев:**\n\n"
    for i, (uid, b) in enumerate(top_users, 1):
      text += f"{i}. `ID: {uid}` — 🪙 `{b}`\n"
    await callback.message.edit_text(
        text, reply_markup=back_kb, parse_mode="Markdown"
    )

  elif action == "daily":
    if last_daily:
      last_time = datetime.fromisoformat(last_daily)
      if datetime.now() - last_time < timedelta(days=1):
        timeLeft = timedelta(days=1) - (datetime.now() - last_time)
        hours = int(timeLeft.total_seconds() // 3600)
        return await callback.answer(
            f"⏳ Рано! Заглядывай через {hours} ч.", show_alert=True
        )

    reward = 100 * (2 if is_vip(vip_exp) else 1)
    cursor.execute(
        "UPDATE users SET balance = balance + ?, last_daily = ? WHERE user_id ="
        " ?",
        (reward, datetime.now().isoformat(), user_id),
    )
    conn.commit()
    await callback.answer(
        f"🎉 Забрал ежедневку! +{reward} монет упало на баланс.",
        show_alert=True,
    )

  elif action == "shop":
    text = (
        "⭐ **Магазин за Звезды (Telegram Stars):**\n\n• Купить монеты:"
        " отправь в чат команду `/buy_coins <кол-во>` (1 звезда = 1 монета)\n•"
        " Купить VIP на 30 дней (x2 бонус + удача в минах): отправь команду"
        " `/buy_vip`"
    )
    await callback.message.edit_text(
        text, reply_markup=back_kb, parse_mode="Markdown"
    )

  elif action == "ref":
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    text = (
        f"🔗 **Твоя рефералка:**\n`{link}`\n\nКидай друзьям, за каждого дадим по"
        " 50 монет тебе и ему!"
    )
    await callback.message.edit_text(
        text, reply_markup=back_kb, parse_mode="Markdown"
    )

  elif action == "back":
    await callback.message.edit_text(
        "👋 Главное меню:", reply_markup=get_main_keyboard()
    )


# --- КОМАНДЫ ДЛЯ ЧАТОВ ---
@router.message(Command("p"))
async def cmd_profile(message: Message):
  bal, vip_exp, _ = get_user_data(message.from_user.id)
  status = "👑 Элитный (Активен)" if is_vip(vip_exp) else "❌ Обычный"
  await message.answer(
      f"🪪 **Паспорт:**\n🆔 ID: `{message.from_user.id}`\n🪙 Баланс:"
      f" `{bal}`\n⭐ VIP: {status}",
      parse_mode="Markdown",
  )


@router.message(Command("b"))
async def cmd_balance(message: Message):
  bal, _, _ = get_user_data(message.from_user.id)
  await message.answer(f"🪙 Твой баланс: `{bal}` монет", parse_mode="Markdown")


@router.message(Command("caz"))
async def cmd_caz(message: Message):
  await message.answer(
      "🎰 **Казино:**\n/slots <ставка> — Слоты\n/dice <ставка> —"
      " Кубик\n/mines <ставка> — Мины\n\n⚡️ Ставка от 5 монет",
      parse_mode="Markdown",
  )


@router.message(Command("top"))
async def cmd_top(message: Message):
  cursor.execute(
      "SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10"
  )
  top_users = cursor.fetchall()
  text = "🏆 **Топ-10 игроков:**\n\n"
  for i, (uid, b) in enumerate(top_users, 1):
    text += f"{i}. `ID: {uid}` — 🪙 `{b}`\n"
  await message.answer(text, parse_mode="Markdown")


@router.message(Command("daily"))
async def cmd_daily(message: Message):
  user_id = message.from_user.id
  bal, vip_exp, last_daily = get_user_data(user_id)
  if last_daily:
    last_time = datetime.fromisoformat(last_daily)
    if datetime.now() - last_time < timedelta(days=1):
      timeLeft = timedelta(days=1) - (datetime.now() - last_time)
      hours = int(timeLeft.total_seconds() // 3600)
      return await message.answer(f"⏳ Рано! Ежедневка будет через {hours} ч.")

  reward = 100 * (2 if is_vip(vip_exp) else 1)
  cursor.execute(
      "UPDATE users SET balance = balance + ?, last_daily = ? WHERE user_id ="
      " ?",
      (reward, datetime.now().isoformat(), user_id),
  )
  conn.commit()
  await message.answer(
      f"🎁 Получил ежедневку: `+{reward}` монет!", parse_mode="Markdown"
  )


@router.message(Command("pay"))
async def cmd_pay(message: Message):
  args = message.text.split()
  if len(args) < 3 or not args[1].isdigit() or not args[2].isdigit():
    return await message.answer("Формат: `/pay <ID> <сумма>`", parse_mode="Markdown")
  target_id, amount = int(args[1]), int(args[2])
  if amount < 5:
    return await message.answer("❌ Минимум для перевода — 5 монет.")
  sender_id = message.from_user.id
  if sender_id == target_id:
    return await message.answer("❌ Самому себе переводить нельзя еж.")
  sender_bal, _, _ = get_user_data(sender_id)
  if sender_bal < amount:
    return await message.answer("❌ На балансе недостаточно монет.")
  get_user_data(target_id)
  cursor.execute(
      "UPDATE users SET balance = balance - ? WHERE user_id = ?",
      (amount, sender_id),
  )
  cursor.execute(
      "UPDATE users SET balance = balance + ? WHERE user_id = ?",
      (amount, target_id),
  )
  conn.commit()
  await message.answer(
      f"✅ Перекинул `{amount}` монет игроку `{target_id}`!", parse_mode="Markdown"
  )


@router.message(Command("addpromo"))
async def cmd_addpromo(message: Message):
  if message.from_user.id != ADMIN_ID:
    return
  args = message.text.split()
  if len(args) < 3:
    return await message.answer("Формат: `/addpromo <код> <награда>`")
  cursor.execute(
      "INSERT OR REPLACE INTO promos (code, reward) VALUES (?, ?)",
      (args[1], int(args[2])),
  )
  conn.commit()
  await message.answer(f"✅ Промокод `{args[1]}` успешно создан!", parse_mode="Markdown")


@router.message(Command("promo"))
async def cmd_promo(message: Message):
  args = message.text.split()
  if len(args) < 2:
    return await message.answer("Формат: `/promo <код>`")
  code = args[1]
  cursor.execute("SELECT reward FROM promos WHERE code = ?", (code,))
  res = cursor.fetchone()
  if not res:
    return await message.answer("❌ Промокод не найден или уже сгорел.")
  reward = res[0]
  user_id = message.from_user.id
  cursor.execute(
      "UPDATE users SET balance = balance + ? WHERE user_id = ?",
      (reward, user_id),
  )
  cursor.execute("DELETE FROM promos WHERE code = ?", (code,))
  conn.commit()
  await message.answer(
      f"🎉 Промокод активирован! Залетело `{reward}` монет!", parse_mode="Markdown"
  )


@router.message(Command("ref"))
async def cmd_ref(message: Message):
  bot_info = await bot.get_me()
  link = f"https://t.me/{bot_info.username}?start=ref_{message.from_user.id}"
  await message.answer(f"🔗 Твоя реферальная ссылка:\n`{link}`", parse_mode="Markdown")


# --- ПЛАТЕЖИ СО ЗВЕЗДАМИ ---
@router.message(Command("buy_coins"))
async def buy_coins(message: Message):
  args = message.text.split()
  if len(args) < 2 or not args[1].isdigit():
    return await message.answer("Формат: `/buy_coins <количество>`")
  amount = int(args[1])
  await message.answer_invoice(
      title="Покупка монет",
      description=f"Покупка {amount} монет (1 звезда = 1 монета)",
      prices=[LabeledPrice(label="Монеты", amount=amount)],
      payload=f"buy_coins_{amount}",
      currency="XTR",
  )


@router.message(Command("buy_vip"))
async def buy_vip(message: Message):
  await message.answer_invoice(
      title="VIP Статус на 30 дней",
      description="Бусты: x2 к монетам в играх и +15% удачи в минах!",
      prices=[LabeledPrice(label="VIP", amount=25)],
      payload="buy_vip_30",
      currency="XTR",
  )


@router.pre_checkout_query()
async def pre_checkout(q):
  await bot.answer_pre_checkout_query(q.id, ok=True)


@router.message(F.successful_payment)
async def success_pay(message: Message):
  payload = message.successful_payment.invoice_payload
  user_id = message.from_user.id
  if payload.startswith("buy_coins_"):
    count = int(payload.split("_")[2])
    cursor.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
        (count, user_id),
    )
  elif payload == "buy_vip_30":
    exp = (datetime.now() + timedelta(days=30)).isoformat()
    cursor.execute(
        "UPDATE users SET vip_expires = ? WHERE user_id = ?", (exp, user_id)
    )
  conn.commit()
  await message.answer("✅ Оплата прошла успешно! Благодарю за поддержку.")


# --- ИГРЫ КАЗИНО ---
@router.message(Command("slots"))
async def play_slots(message: Message):
  args = message.text.split()
  if len(args) < 2 or not args[1].isdigit() or int(args[1]) < 5:
    return await message.answer("❌ Ставка от 5 монет: `/slots <ставка>`")
  bet = int(args[1])
  bal, vip_exp, _ = get_user_data(message.from_user.id)
  if bal < bet:
    return await message.answer("❌ Мало монет на балансе!")

  cursor.execute(
      "UPDATE users SET balance = balance - ? WHERE user_id = ?",
      (bet, message.from_user.id),
  )
  msg = await message.answer_dice("🎰")
  await asyncio.sleep(2.5)

  if msg.dice.value in [1, 22, 43, 64]:
    win = (bet * 5) * (2 if is_vip(vip_exp) else 1)
    cursor.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
        (win, message.from_user.id),
    )
    await message.answer(
        f"🎰 **ДЖЕКПОТ!** Выиграл `{win}` монет!", parse_mode="Markdown"
    )
  else:
    await message.answer("😢 Мимо, бро. Повезет в следующий раз.")
  conn.commit()


@router.message(Command("dice"))
async def play_dice(message: Message):
  args = message.text.split()
  if len(args) < 2 or not args[1].isdigit() or int(args[1]) < 5:
    return await message.answer("❌ Ставка от 5 монет: `/dice <ставка>`")
  bet = int(args[1])
  bal, vip_exp, _ = get_user_data(message.from_user.id)
  if bal < bet:
    return await message.answer("❌ Недостаточно монет!")

  cursor.execute(
      "UPDATE users SET balance = balance - ? WHERE user_id = ?",
      (bet, message.from_user.id),
  )
  msg = await message.answer_dice("🎲")
  await asyncio.sleep(3)

  if msg.dice.value >= 4:
    win = (bet * 2) * (2 if is_vip(vip_exp) else 1)
    cursor.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
        (win, message.from_user.id),
    )
    await message.answer(
        f"🎯 Выпало {msg.dice.value}! Забирай выигрыш: `{win}` монет!",
        parse_mode="Markdown",
    )
  else:
    await message.answer(f"😢 Выпало {msg.dice.value}. Луз.")
  conn.commit()


@router.message(Command("mines"))
async def play_mines(message: Message):
  args = message.text.split()
  if len(args) < 2 or not args[1].isdigit() or int(args[1]) < 5:
    return await message.answer("❌ Ставка от 5 монет: `/mines <ставка>`")
  bet = int(args[1])
  bal, vip_exp, _ = get_user_data(message.from_user.id)
  if bal < bet:
    return await message.answer("❌ Недостаточно монет!")

  chance = 0.25
  if is_vip(vip_exp):
    chance -= 0.15

  cursor.execute(
      "UPDATE users SET balance = balance - ? WHERE user_id = ?",
      (bet, message.from_user.id),
  )

  if random.random() > chance:
    win = int(bet * 2) * (2 if is_vip(vip_exp) else 1)
    cursor.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
        (win, message.from_user.id),
    )
    await message.answer(
        f"💰 **Изи катка!** Поле чистое. Выигрыш: `{win}` монет!",
        parse_mode="Markdown",
    )
  else:
    await message.answer(
        "💥 **БУХ!** Нарвался на мину, луз.", parse_mode="Markdown"
    )
  conn.commit()


async def main():
  dp.include_router(router)
  await bot.delete_webhook(drop_pending_updates=True)
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())

