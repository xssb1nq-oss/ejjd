from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def main_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Каталог"), KeyboardButton(text="📋 Мои заказы")],
            [KeyboardButton(text="💬 Поддержка"), KeyboardButton(text="ℹ️ О нас")],
        ],
        resize_keyboard=True
    )


def admin_menu_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📦 Заказы")],
            [KeyboardButton(text="🗝 Добавить ключи"), KeyboardButton(text="➕ Добавить товар")],
            [KeyboardButton(text="🛒 Каталог"), KeyboardButton(text="👥 Пользователи")],
        ],
        resize_keyboard=True
    )


def categories_kb(categories):
    buttons = [[InlineKeyboardButton(text=f"📁 {cat}", callback_data=f"cat_{cat}")] for cat in categories]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def products_kb(products, category):
    buttons = []
    for p in products:
        pid, name, desc, price, duration, cat, active = p
        buttons.append([InlineKeyboardButton(
            text=f"⏱ {duration} — {price} ₴",
            callback_data=f"product_{pid}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_cats")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_detail_kb(product_id, category):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Купить", callback_data=f"buy_{product_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"cat_{category}")],
    ])


def payment_kb(order_id, card_number):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Скопировать карту", callback_data=f"copy_card_{card_number}")],
        [InlineKeyboardButton(text="✅ Я оплатил — отправить чек", callback_data=f"paid_{order_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_{order_id}")],
    ])


def admin_order_kb(order_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{order_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{order_id}"),
        ]
    ])


def back_to_cats_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ В каталог", callback_data="back_to_cats")]
    ])
