from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
import keyboards as kb
from config import (
    ADMIN_IDS, BANK_NAME, CARD_NUMBER, CARD_HOLDER,
    CURRENCY_SYMBOL, NOTIFY_CHANNEL
)

router = Router()


class OrderState(StatesGroup):
    waiting_receipt = State()


# ── /start ────────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message):
    db.register_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name or ""
    )
    db.init_db()

    name = message.from_user.first_name or "друг"
    await message.answer(
        f"👋 Привет, <b>{name}</b>!\n\n"
        f"🔑 Добро пожаловать в <b>ANONYM KEYS</b>\n\n"
        f"Мы продаём лицензионные ключи и подписки.\n"
        f"Выбери раздел в меню ниже 👇",
        parse_mode="HTML",
        reply_markup=kb.main_menu_kb()
    )


# ── Каталог ───────────────────────────────────────────────
@router.message(F.text == "🛒 Каталог")
async def show_catalog(message: Message):
    categories = db.get_categories()
    if not categories:
        await message.answer("😔 Каталог пуст. Скоро добавим товары!")
        return
    await message.answer(
        "📁 <b>Выбери категорию:</b>",
        parse_mode="HTML",
        reply_markup=kb.categories_kb(categories)
    )


@router.callback_query(F.data == "back_to_cats")
async def back_to_categories(call: CallbackQuery):
    categories = db.get_categories()
    await call.message.edit_text(
        "📁 <b>Выбери категорию:</b>",
        parse_mode="HTML",
        reply_markup=kb.categories_kb(categories)
    )


@router.callback_query(F.data.startswith("cat_"))
async def show_category(call: CallbackQuery):
    category = call.data.split("cat_")[1]
    products = db.get_products_by_category(category)
    if not products:
        await call.answer("Нет доступных товаров", show_alert=True)
        return

    # Берём описание из первого товара
    desc = products[0][2]
    text = (
        f"📦 <b>{category}</b>\n\n"
        f"{desc}\n\n"
        f"✅ Без бана\n"
        f"⚡ Быстрая установка\n"
        f"🔄 Регулярные обновления\n\n"
        f"⏳ <b>Выбери тариф:</b>"
    )
    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.products_kb(products, category)
    )


@router.callback_query(F.data.startswith("product_"))
async def show_product(call: CallbackQuery):
    product_id = int(call.data.split("product_")[1])
    product = db.get_product(product_id)
    if not product:
        await call.answer("Товар не найден", show_alert=True)
        return

    pid, name, desc, price, duration, category, active = product
    free_keys = db.count_free_keys(pid)
    stock_emoji = "✅" if free_keys > 0 else "❌"
    stock_text = f"В наличии: {free_keys} шт." if free_keys > 0 else "Нет в наличии"

    text = (
        f"🔑 <b>{name}</b>\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"⏱ Тариф: <b>{duration}</b>\n"
        f"💰 Цена: <b>{price} {CURRENCY_SYMBOL}</b>\n"
        f"{stock_emoji} {stock_text}\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"📝 {desc}"
    )
    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.product_detail_kb(pid, category)
    )


# ── Покупка ───────────────────────────────────────────────
@router.callback_query(F.data.startswith("buy_"))
async def buy_product(call: CallbackQuery, state: FSMContext):
    product_id = int(call.data.split("buy_")[1])
    product = db.get_product(product_id)
    if not product:
        await call.answer("Товар не найден", show_alert=True)
        return

    pid, name, desc, price, duration, category, active = product

    # Создаём заказ
    username = call.from_user.username or str(call.from_user.id)
    order_id = db.create_order(
        call.from_user.id, username, pid,
        f"{name} ({duration})", price
    )

    await state.set_state(OrderState.waiting_receipt)
    await state.update_data(order_id=order_id, product_id=pid)

    text = (
        f"💳 <b>Оплата гривнями</b>\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"🛒 Товар: <b>{name}</b>\n"
        f"⏱ Тариф: <b>{duration}</b>\n"
        f"💰 До оплаты: <b>{price} {CURRENCY_SYMBOL}</b>\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"🏦 Банк: <b>{BANK_NAME}</b>\n"
        f"💳 Карта: <code>{CARD_NUMBER}</code>\n"
        f"👤 Получатель: <b>{CARD_HOLDER}</b>\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"📎 Переведите <b>точную сумму</b> и нажмите\n"
        f"«Я оплатил» — отправьте чек (фото/PDF)."
    )
    await call.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.payment_kb(order_id, CARD_NUMBER)
    )


@router.callback_query(F.data.startswith("copy_card_"))
async def copy_card(call: CallbackQuery):
    card = call.data.split("copy_card_")[1]
    await call.answer(f"Карта: {card}", show_alert=True)


@router.callback_query(F.data.startswith("cancel_"))
async def cancel_order(call: CallbackQuery, state: FSMContext):
    order_id = int(call.data.split("cancel_")[1])
    db.reject_order(order_id)
    await state.clear()
    await call.message.edit_text(
        "❌ Заказ отменён.\n\nВозвращайся, когда будешь готов! 👋",
        reply_markup=kb.back_to_cats_kb()
    )


@router.callback_query(F.data.startswith("paid_"))
async def user_paid(call: CallbackQuery, state: FSMContext):
    await call.message.answer(
        "📸 Отправьте чек оплаты:\n"
        "<i>(фото, PDF или скриншот)</i>",
        parse_mode="HTML"
    )
    await call.answer()


# Получение чека — фото
@router.message(OrderState.waiting_receipt, F.photo)
async def receipt_photo(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    order_id = data.get("order_id")
    order = db.get_order(order_id)
    if not order:
        await state.clear()
        return

    await _notify_admins(bot, message, order, "фото")
    await state.clear()
    await message.answer(
        "✅ <b>Чек получен!</b>\n\n"
        "Мы проверяем оплату — ключ придёт в течение нескольких минут.\n"
        "Спасибо за ожидание! 🙏",
        parse_mode="HTML"
    )


# Получение чека — документ (PDF)
@router.message(OrderState.waiting_receipt, F.document)
async def receipt_doc(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    order_id = data.get("order_id")
    order = db.get_order(order_id)
    if not order:
        await state.clear()
        return

    await _notify_admins(bot, message, order, "документ")
    await state.clear()
    await message.answer(
        "✅ <b>Чек получен!</b>\n\n"
        "Мы проверяем оплату — ключ придёт в течение нескольких минут.\n"
        "Спасибо за ожидание! 🙏",
        parse_mode="HTML"
    )


async def _notify_admins(bot: Bot, message: Message, order, receipt_type: str):
    oid, uid, uname, pid, pname, amount, status, created, confirmed, key = order
    username_link = f"@{uname}" if uname else f"<a href='tg://user?id={uid}'>Пользователь</a>"

    text = (
        f"🔔 <b>Новый чек на оплату!</b>\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"📋 Заказ: <b>#{oid}</b>\n"
        f"👤 Пользователь: {username_link} (<code>{uid}</code>)\n"
        f"🛒 Товар: <b>{pname}</b>\n"
        f"💰 Сумма: <b>{amount} ₴</b>\n"
        f"📎 Тип чека: {receipt_type}\n"
        f"━━━━━━━━━━━━━━━━━"
    )

    for admin_id in ADMIN_IDS:
        try:
            # Пересылаем чек
            await message.forward(admin_id)
            # Отправляем инфо с кнопками
            await bot.send_message(
                admin_id,
                text,
                parse_mode="HTML",
                reply_markup=kb.admin_order_kb(oid)
            )
        except Exception as e:
            print(f"Не удалось отправить уведомление admin {admin_id}: {e}")


# ── Мои заказы ────────────────────────────────────────────
@router.message(F.text == "📋 Мои заказы")
async def my_orders(message: Message):
    orders = db.get_user_orders(message.from_user.id)
    if not orders:
        await message.answer("📭 У тебя пока нет заказов.\n\nЗагляни в каталог! 🛒")
        return

    status_map = {
        "pending": "⏳ Ожидает",
        "confirmed": "✅ Выполнен",
        "rejected": "❌ Отклонён"
    }

    text = "📋 <b>Твои последние заказы:</b>\n\n"
    for order in orders:
        oid, uid, uname, pid, pname, amount, status, created, confirmed, key = order
        s = status_map.get(status, status)
        text += f"#{oid} | {pname} | {amount} ₴ | {s}\n"
        if status == "confirmed" and key:
            text += f"   🔑 Ключ: <code>{key}</code>\n"
        text += "\n"

    await message.answer(text, parse_mode="HTML")


# ── Поддержка ─────────────────────────────────────────────
@router.message(F.text == "💬 Поддержка")
async def support(message: Message):
    await message.answer(
        "💬 <b>Поддержка</b>\n\n"
        "Если у тебя возникли вопросы или проблемы:\n\n"
        "👉 Напиши администратору напрямую\n"
        "📧 Или используй команду /help с описанием проблемы",
        parse_mode="HTML"
    )


# ── О нас ─────────────────────────────────────────────────
@router.message(F.text == "ℹ️ О нас")
async def about(message: Message):
    await message.answer(
        "🔑 <b>ANONYM KEYS</b>\n\n"
        "Мы — надёжный магазин цифровых ключей и подписок.\n\n"
        "✅ <b>Наши гарантии:</b>\n"
        "• Без бана — 100% безопасно\n"
        "• Быстрая выдача после оплаты\n"
        "• Поддержка 24/7\n"
        "• Регулярные обновления\n\n"
        "💎 Работаем с 2023 года",
        parse_mode="HTML"
    )
