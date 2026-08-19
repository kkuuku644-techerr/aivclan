import asyncio
from datetime import datetime, timedelta
import random
import sqlite3
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import LabeledPrice, Message

# ТВОИ ДАННЫЕ
TOKEN = "8983343344:AAFk61fK5vLB7yn1k9OP0MtTAbenRyobBcI"
ADMIN_ID = 7959524856

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
          "❌ Этот бот является приватным клановым ботом и может быть добавлен"
          " только создателем!",
      )
      await bot.leave_chat(event.chat.id)


# --- ПАСПОРТ И ПРОФИЛЬ ---
@router.message(Command("p"))
async def cmd_profile(message: Message):
  user_id = message.from_user.id
  bal, vip_exp, _ = get_user_data(user_id)
  status = "👑 Активен" if is_vip(vip_exp) else "❌ Нет"

  text = (
      f"🪪 **Паспорт клана Evade**\n\n"
      f"🆔 ID: `{user_id}`\n"
      f"🪙 Баланс монеток: `{bal}`\n"
      f"⭐ VIP Статус: {status}"
  )
  await message.answer(text, parse_mode="Markdown")


@router.message(Command("b"))
async def cmd_balance(message: Message):
  bal, _, _ = get_user_data(message.from_user.id)
  await message.answer(
      f"🪙 Ваш текущий баланс: `{bal}` монеток", parse_mode="Markdown"
  )


# --- ЕЖЕДНЕВНЫЙ БОНУС ---
@router.message(Command("daily"))
async def cmd_daily(message: Message):
  user_id = message.from_user.id
  bal, vip_exp, last_daily = get_user_data(user_id)

  if last_daily:
    last_time = datetime.fromisoformat(last_daily)
    if datetime.now() - last_time < timedelta(days=1):
      timeLeft = timedelta(days=1) - (datetime.now() - last_time)
      hours = int(timeLeft.total_seconds() // 3600)
      return await message.answer(
          f"⏳ Награда уже получена. Ждите еще {hours} ч."
      )

  reward = 100 * (2 if is_vip(vip_exp) else 1)
  cursor.execute(
      "UPDATE users SET balance = balance + ?, last_daily = ? WHERE user_id ="
      " ?",
      (reward, datetime.now().isoformat(), user_id),
  )
  conn.commit()
  await message.answer(
      f"🎁 Вы получили ежедневный бонус: `{reward}` монеток!",
      parse_mode="Markdown",
  )


# --- ТОП ИГРОКОВ ---
@router.message(Command("top"))
async def cmd_top(message: Message):
  cursor.execute(
      "SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10"
  )
  top_users = cursor.fetchall()

  text = "🏆 **Топ-10 игроков клана:**\n\n"
  for i, (uid, bal) in enumerate(top_users, 1):
    text += f"{i}. `ID: {uid}` — 🪙 `{bal}`\n"

  await message.answer(text, parse_mode="Markdown")


# --- ПЕРЕВОД МОНЕТ (/pay) ---
@router.message(Command("pay"))
async def cmd_pay(message: Message):
  args = message.text.split()
  if len(args) < 3 or not args[1].isdigit() or not args[2].isdigit():
    return await message.answer(
        "Использование: `/pay <ID_игрока> <сумма>`", parse_mode="Markdown"
    )

  target_id = int(args[1])
  amount = int(args[2])

  if amount < 5:
    return await message.answer("❌ Минимальная сумма перевода: 5 монет.")

  sender_id = message.from_user.id
  if sender_id == target_id:
    return await message.answer("❌ Нельзя переводить монеты самому себе.")

  sender_bal, _, _ = get_user_data(sender_id)
  if sender_bal < amount:
    return await message.answer("❌ У вас недостаточно монеток.")

  get_user_data(target_id)  # создаем получателя в базе, если его не было

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
      f"✅ Вы успешно передали `{amount}` монеток игроку `{target_id}`!",
      parse_mode="Markdown",
  )


# --- ПРОМОКОДЫ ---
@router.message(Command("addpromo"))
async def cmd_addpromo(message: Message):
  if message.from_user.id != ADMIN_ID:
    return
  args = message.text.split()
  if len(args) < 3:
    return await message.answer("Использование: `/addpromo <код> <награда>`")
  cursor.execute(
      "INSERT OR REPLACE INTO promos (code, reward) VALUES (?, ?)",
      (args[1], int(args[2])),
  )
  conn.commit()
  await message.answer(f"✅ Промокод `{args[1]}` создан!", parse_mode="Markdown")


@router.message(Command("promo"))
async def cmd_promo(message: Message):
  args = message.text.split()
  if len(args) < 2:
    return await message.answer("Использование: `/promo <код>`")
  code = args[1]

  cursor.execute("SELECT reward FROM promos WHERE code = ?", (code,))
  res = cursor.fetchone()
  if not res:
    return await message.answer("❌ Промокод не найден или устарел.")

  reward = res[0]
  user_id = message.from_user.id
  cursor.execute(
      "UPDATE users SET balance = balance + ? WHERE user_id = ?",
      (reward, user_id),
  )
  cursor.execute("DELETE FROM promos WHERE code = ?", (code,))
  conn.commit()
  await message.answer(
      f"🎉 Промокод активирован! Вы получили `{reward}` монеток!",
      parse_mode="Markdown",
  )


# --- РЕФЕРАЛЬНАЯ СИСТЕМА ---
@router.message(Command("ref"))
async def cmd_ref(message: Message):
  user_id = message.from_user.id
  bot_info = await bot.get_me()
  link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
  await message.answer(
      f"🔗 Ваша реферальная ссылка:\n`{link}`\n\nПриглашайте друзей и получайте"
      " бонусы!",
      parse_mode="Markdown",
  )


@router.message(Command("start"))
async def cmd_start(message: Message):
  args = message.text.split()
  user_id = message.from_user.id
  get_user_data(user_id)

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
            "🎁 Вы активировали реферальную ссылку и получили 50 монет!"
        )

  await message.answer(
      "👋 Добро пожаловать в клановый бот **Evade**!\nИспользуйте /p для"
      " просмотра паспорта и /caz для списка игр.",
      parse_mode="Markdown",
  )


# --- ПОКУПКА МОНЕТ И VIP ЗА ЗВЕЗДЫ ---
@router.message(Command("buy_coins"))
async def buy_coins(message: Message):
  args = message.text.split()
  if len(args) < 2 or not args[1].isdigit():
    return await message.answer("Использование: `/buy_coins <количество>`")
  amount = int(args[1])
  await message.answer_invoice(
      title="Покупка монет Evade",
      description=f"Покупка {amount} монеток (1 звезда = 1 монета)",
      prices=[LabeledPrice(label="Монетки", amount=amount)],
      payload=f"buy_coins_{amount}",
      currency="XTR",
  )


@router.message(Command("buy_vip"))
async def buy_vip(message: Message):
  await message.answer_invoice(
      title="VIP Статус на 30 дней",
      description=(
          "Преимущества VIP: x2 к монетам во всех играх и +15% к удаче в минах!"
      ),
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
  await message.answer("✅ Успешная покупка! Спасибо за поддержку.")


# --- КАЗИНО И ИГРЫ ---
@router.message(Command("caz"))
async def cmd_caz(message: Message):
  await message.answer(
      "🎰 **Казино клана Evade**\n\n/slots <ставка> — Слоты\n/dice <ставка> —"
      " Кубик\n/mines <ставка> — Мины\n\n⚡️ Минимальная ставка: `5` монет",
      parse_mode="Markdown",
  )


@router.message(Command("slots"))
async def play_slots(message: Message):
  args = message.text.split()
  if len(args) < 2 or not args[1].isdigit() or int(args[1]) < 5:
    return await message.answer(
        "❌ Минимальная ставка: `/slots <ставка от 5>`", parse_mode="Markdown"
    )
  bet = int(args[1])

  bal, vip_exp, _ = get_user_data(message.from_user.id)
  if bal < bet:
    return await message.answer("❌ Недостаточно монеток на балансе!")

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
        f"🎉 **ДЖЕКПОТ!** Вы выиграли `{win}` монеток!", parse_mode="Markdown"
    )
  else:
    await message.answer("😢 К сожалению, вы проиграли ставку.")
  conn.commit()


@router.message(Command("dice"))
async def play_dice(message: Message):
  args = message.text.split()
  if len(args) < 2 or not args[1].isdigit() or int(args[1]) < 5:
    return await message.answer(
        "❌ Минимальная ставка: `/dice <ставка от 5>`", parse_mode="Markdown"
    )
  bet = int(args[1])

  bal, vip_exp, _ = get_user_data(message.from_user.id)
  if bal < bet:
    return await message.answer("❌ Недостаточно монеток!")

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
        f"🎯 Выброшено {msg.dice.value}! Победа, вы выиграли `{win}` монеток!",
        parse_mode="Markdown",
    )
  else:
    await message.answer(f"😢 Выброшено {msg.dice.value}. Поражение.")
  conn.commit()


@router.message(Command("mines"))
async def play_mines(message: Message):
  args = message.text.split()
  if len(args) < 2 or not args[1].isdigit() or int(args[1]) < 5:
    return await message.answer(
        "❌ Минимальная ставка: `/mines <ставка от 5>`", parse_mode="Markdown"
    )
  bet = int(args[1])

  bal, vip_exp, _ = get_user_data(message.from_user.id)
  if bal < bet:
    return await message.answer("❌ Недостаточно монеток!")

  # Шанс бомбы базовый 25%, для ВИП снижаем на 15%
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
        f"💰 **Успех!** Поле пройдено. Выигрыш: `{win}` монеток!",
        parse_mode="Markdown",
    )
  else:
    await message.answer(
        "💥 **БУХ!** Вы нарвались на мину и потеряли ставку.",
        parse_mode="Markdown",
    )
  conn.commit()


async def main():
  dp.include_router(router)
  await bot.delete_webhook(drop_pending_updates=True)
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())

