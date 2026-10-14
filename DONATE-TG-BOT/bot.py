import asyncio
import logging
from datetime import datetime
from typing import Optional

import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "YOUR_BOTFATHER_TOKEN"
CRYPTO_PAY_TOKEN = "YOUR_CRYPTOPAY_TOKEN"

CRYPTO_PAY_API = "https://pay.crypt.bot/api"   # тестнет: https://testnet-pay.crypt.bot/api
ASSET = "USDT"
TIP_AMOUNTS = [1, 3, 5, 10, 25]

TEXT_START = (
    "👋 Привет, {name}!\n\n"
    "☕ Это бот для чаевых.\n"
    "Выбери сумму — и я создам счёт в крипте ({asset})."
)
TEXT_THANKS = (
    "🙏 Спасибо за поддержку!\n\n"
    "Нажми <b>«Оплатить»</b> — счёт откроется прямо в Telegram.\n"
    "После оплаты нажми <b>«Проверить оплату»</b>."
)
# =================================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ---------- Crypto Pay ----------
async def crypto_api(method: str, payload: Optional[dict] = None) -> dict:
    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
    async with aiohttp.ClientSession() as s:
        async with s.post(
            "{}/{}".format(CRYPTO_PAY_API, method),
            json=payload or {},
            headers=headers,
        ) as r:
            data = await r.json()
            if not data.get("ok"):
                raise RuntimeError("CryptoPay: {}".format(data))
            return data["result"]


async def create_invoice(amount: float, user_id: int) -> dict:
    return await crypto_api("createInvoice", {
        "asset": ASSET,
        "amount": str(amount),
        "description": "Чайевые ☕",
        "payload": "tip:{}:{}".format(user_id, int(datetime.utcnow().timestamp())),
        "expires_in": 3600,
    })


async def get_invoice(invoice_id: int) -> dict:
    res = await crypto_api("getInvoices", {"invoice_ids": str(invoice_id)})
    items = res.get("items", [])
    return items[0] if items else {}


# ---------- Клавиатуры ----------
def tips_keyboard() -> InlineKeyboardMarkup:
    rows, row = [], []
    for a in TIP_AMOUNTS:
        row.append(InlineKeyboardButton(
            text="💸 {} {}".format(a, ASSET),
            callback_data="tip:{}".format(a),
        ))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="✏️ Своя сумма", callback_data="tip:custom")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def invoice_keyboard(pay_url: str, invoice_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Оплатить", url=pay_url)],
        [InlineKeyboardButton(text="✅ Проверить оплату",
                              callback_data="check:{}".format(invoice_id))],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")],
    ])


# ---------- Хэндлеры ----------
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        TEXT_START.format(name=message.from_user.first_name, asset=ASSET),
        reply_markup=tips_keyboard(),
    )


@dp.callback_query(F.data == "back")
async def back_handler(call: CallbackQuery):
    await call.message.edit_text(
        TEXT_START.format(name=call.from_user.first_name, asset=ASSET),
        reply_markup=tips_keyboard(),
    )
    await call.answer()


@dp.callback_query(F.data == "tip:custom")
async def custom_tip(call: CallbackQuery):
    await call.message.edit_text(
        "✏️ Напиши сумму в {} (например: <code>4.5</code>).".format(ASSET),
        parse_mode="HTML",
    )
    await call.answer()


@dp.callback_query(F.data.startswith("tip:"))
async def tip_handler(call: CallbackQuery):
    amount = float(call.data.split(":", 1)[1])
    await send_invoice(call.message, amount, call.from_user.id)
    await call.answer()


@dp.message(F.text.regexp(r"^\d+(\.\d+)?$"))
async def custom_amount(message: Message):
    amount = float(message.text)
    if amount <= 0:
        await message.answer("Сумма должна быть больше нуля 🙂")
        return
    await send_invoice(message, amount, message.from_user.id)


async def send_invoice(message: Message, amount: float, user_id: int):
    try:
        inv = await create_invoice(amount, user_id)
    except Exception as e:
        logging.exception("Ошибка создания инвойса")
        await message.answer("⚠️ Не удалось создать счёт: {}".format(e))
        return
    await message.answer(
        TEXT_THANKS,
        reply_markup=invoice_keyboard(inv["bot_invoice_url"], inv["invoice_id"]),
        parse_mode="HTML",
    )


@dp.callback_query(F.data.startswith("check:"))
async def check_payment(call: CallbackQuery):
    invoice_id = int(call.data.split(":", 1)[1])
    try:
        inv = await get_invoice(invoice_id)
    except Exception:
        logging.exception("Ошибка проверки")
        await call.answer("Ошибка проверки, попробуй позже", show_alert=True)
        return

    status = inv.get("status")
    if status == "paid":
        await call.message.edit_text(
            "✅ Оплата получена! Спасибо за {} {} 🙏".format(inv["amount"], inv["asset"])
        )
        await call.answer("Оплата подтверждена ✅")
    elif status in ("expired", "cancelled"):
        await call.answer("Счёт просрочен или отменён", show_alert=True)
    else:
        await call.answer("Платёж ещё не поступил. Попробуй через минуту.", show_alert=True)


async def main():
    try:
        me = await crypto_api("getMe")
        print("✅ Crypto Pay: @{} (app_id={})".format(me["name"], me["app_id"]))
    except Exception as e:
        print("❌ Crypto Pay: {}".format(e))
        return

    try:
        tg = await bot.get_me()
        print("✅ Telegram-бот: @{}".format(tg.username))
    except Exception as e:
        print("❌ Telegram: {}".format(e))
        return

    print("🚀 Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())