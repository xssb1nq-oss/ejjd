from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
import keyboards as kb
from config import ADMIN_IDS

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class AddKeyState(StatesGroup):
    choose_product = State()
    enter_keys = State()


class AddProductState(StatesGroup):
    name = State()
    description = State()
    price = State()
    duration = State()
    category = State()


# ── Фильтр: только для админа ─────────────────────────────
@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return
    users, confirmed, revenue, pending = db.get_stats()
    await message.answer(
        f"🔐 <b>Панель администратора</b>\n\n"
        f"👥 Пользователей: <b>{users}</b>\n"
        f"✅ Выполнено заказов: <b>{confirmed}</b>\n"
        f"💰 Выручка: <b>{revenue} ₴</b>\n"
        f"⏳ Ожидают подтверждения: <b>{pending}</b>",
        parse_mode="HTML",
        reply_markup=kb.admin_menu_kb()
    )


# ── Статистика ────────────────────────────────────────────
@router.message(F.text == "📊 Статистика")
async def admin_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    users, confirmed, revenue, pending = db.get_stats()
    await message.answer(
        f"📊 <b>Статистика магазина</b>\n\n"
        f"👥 Всего пользователей: <b>{users}</b>\n"
        f"✅ Выполнено заказов: <b>{confirmed}</b>\n"
        f"❌ Ожидают: <b>{pending}</b>\n"
        f"💰 Общая выручка: <b>{revenue} ₴</b>",
        parse_mode="HTML"
    )


# ── Ожидающие заказы ──────────────────────────────────────
@router.message(F.text == "📦 Заказы")
async def admin_orders(message: Message):
    if not is_admin(message.from_user.id):
        return
    orders = db.get_pending_orders()
    if not orders:
        await message.answer("✅ Нет ожидающих заказов!")
        return
    for order in orders:
        oid, uid, uname, pid, pname, amount, status, created, confirmed, key = order
        ulink = f"@{uname}" if uname else f"ID:{uid}"
        await message.answer(
            f"📋 Заказ <b>#{oid}</b>\n"
            f"👤 {ulink} (<code>{uid}</code>)\n"
            f"🛒 {pname}\n"
            f"💰 {amount} ₴\n"
            f"🕐 {created}",
            parse_mode="HTML",
            reply_markup=kb.admin_order_kb(oid)
        )


# ── Подтверждение заказа ──────────────────────────────────
@router.callback_query(F.data.startswith("confirm_"))
async def confirm_order(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    order_id = int(call.data.split("confirm_")[1])
    order = db.get_order(order_id)
    if not order:
        await call.answer("Заказ не найден", show_alert=True)
        return

    oid, uid, uname, pid, pname, amount, status, created, confirmed, key = order

    if status != "pending":
        await call.answer("Заказ уже обработан!", show_alert=True)
        return

    # Ищем свободный ключ
    key_row = db.get_free_key(pid)

    if key_row:
        key_id, key_value = key_row
        db.use_key(key_id, uid)
        db.confirm_order(order_id, key_value)

        # Отправляем ключ пользователю
        try:
            await bot.send_message(
                uid,
                f"✅ <b>Оплата подтверждена!</b>\n\n"
                f"🛒 Товар: <b>{pname}</b>\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"🔑 Твой ключ:\n"
                f"<code>{key_value}</code>\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"✨ Спасибо за покупку!\n"
                f"⭐ Оставь отзыв в поддержке",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Не удалось отправить ключ: {e}")

        await call.message.edit_text(
            f"✅ <b>Заказ #{order_id} подтверждён</b>\n"
            f"Ключ <code>{key_value}</code> отправлен пользователю.",
            parse_mode="HTML"
        )
        await call.answer("✅ Подтверждено!")
    else:
        # Ключей нет — подтверждаем без автовыдачи
        db.confirm_order(order_id, "выдано вручную")
        await bot.send_message(
            uid,
            f"✅ <b>Оплата подтверждена!</b>\n\n"
            f"🛒 Товар: <b>{pname}</b>\n\n"
            f"⏳ Ключ выдаётся вручную — ожидай сообщения от администратора.",
            parse_mode="HTML"
        )
        await call.message.edit_text(
            f"⚠️ Заказ #{order_id} подтверждён, но <b>ключей нет в базе!</b>\n"
            f"Выдай ключ пользователю <code>{uid}</code> вручную.",
            parse_mode="HTML"
        )
        await call.answer("⚠️ Ключей нет, уведоми пользователя!", show_alert=True)


# ── Отклонение заказа ─────────────────────────────────────
@router.callback_query(F.data.startswith("reject_"))
async def reject_order(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return

    order_id = int(call.data.split("reject_")[1])
    order = db.get_order(order_id)
    if not order:
        await call.answer("Заказ не найден", show_alert=True)
        return

    oid, uid, uname, pid, pname, amount, status, created, confirmed, key = order

    if status != "pending":
        await call.answer("Заказ уже обработан!", show_alert=True)
        return

    db.reject_order(order_id)

    try:
        await bot.send_message(
            uid,
            f"❌ <b>Оплата не подтверждена</b>\n\n"
            f"Заказ: <b>{pname}</b>\n\n"
            f"Если вы оплатили — обратитесь в поддержку /help",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await call.message.edit_text(
        f"❌ <b>Заказ #{order_id} отклонён.</b>",
        parse_mode="HTML"
    )
    await call.answer("❌ Отклонено")


# ── Добавление ключей ─────────────────────────────────────
@router.message(F.text == "🗝 Добавить ключи")
async def add_keys_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    products = db.get_all_products()
    if not products:
        await message.answer("Нет товаров!")
        return

    text = "📦 <b>Выбери товар (введи номер):</b>\n\n"
    for p in products:
        pid, name, desc, price, duration, cat, active = p
        free = db.count_free_keys(pid)
        status = "✅" if active else "❌"
        text += f"{pid}. {status} {name} ({duration}) — {price} ₴ | 🗝 {free} шт.\n"

    await message.answer(text, parse_mode="HTML")
    await state.set_state(AddKeyState.choose_product)


@router.message(AddKeyState.choose_product)
async def add_keys_choose(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        pid = int(message.text.strip())
    except ValueError:
        await message.answer("Введи числовой ID товара")
        return

    product = db.get_product(pid)
    if not product:
        await message.answer("Товар не найден")
        return

    await state.update_data(product_id=pid, product_name=product[1])
    await state.set_state(AddKeyState.enter_keys)
    await message.answer(
        f"🗝 Добавляем ключи для: <b>{product[1]} ({product[4]})</b>\n\n"
        f"Введи ключи <b>каждый с новой строки</b>:",
        parse_mode="HTML"
    )


@router.message(AddKeyState.enter_keys)
async def add_keys_enter(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    pid = data["product_id"]
    pname = data["product_name"]

    keys = [k.strip() for k in message.text.strip().split("\n") if k.strip()]
    for key in keys:
        db.add_key(pid, key)

    await state.clear()
    await message.answer(
        f"✅ Добавлено <b>{len(keys)}</b> ключей для <b>{pname}</b>!",
        parse_mode="HTML"
    )


# ── Добавление товара ─────────────────────────────────────
@router.message(F.text == "➕ Добавить товар")
async def add_product_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AddProductState.name)
    await message.answer("📦 Введи название товара:")


@router.message(AddProductState.name)
async def add_product_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddProductState.description)
    await message.answer("📝 Введи описание:")


@router.message(AddProductState.description)
async def add_product_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(AddProductState.price)
    await message.answer("💰 Введи цену (только число, в гривнях):")


@router.message(AddProductState.price)
async def add_product_price(message: Message, state: FSMContext):
    try:
        price = int(message.text.strip())
    except ValueError:
        await message.answer("Введи числовое значение!")
        return
    await state.update_data(price=price)
    await state.set_state(AddProductState.duration)
    await message.answer("⏱ Введи тариф (например: 1 день, 7 дней, 30 дней):")


@router.message(AddProductState.duration)
async def add_product_duration(message: Message, state: FSMContext):
    await state.update_data(duration=message.text.strip())
    await state.set_state(AddProductState.category)
    await message.answer("📁 Введи категорию (например: iOS, Android, PC):")


@router.message(AddProductState.category)
async def add_product_category(message: Message, state: FSMContext):
    await state.update_data(category=message.text.strip())
    data = await state.get_data()

    pid = db.add_product(
        data["name"], data["description"],
        data["price"], data["duration"], data["category"]
    )
    await state.clear()
    await message.answer(
        f"✅ <b>Товар добавлен!</b>\n\n"
        f"ID: {pid}\n"
        f"Название: {data['name']}\n"
        f"Тариф: {data['duration']}\n"
        f"Цена: {data['price']} ₴\n"
        f"Категория: {data['category']}\n\n"
        f"Теперь добавь ключи через «🗝 Добавить ключи»",
        parse_mode="HTML"
    )
