import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

if not BOT_TOKEN or not ADMIN_ID:
    raise ValueError("BOT_TOKEN or ADMIN_ID is not set")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Определение состояний FSM
class Form(StatesGroup):
    name = State()
    phone = State()
    direction = State()
    day = State()

# Клавиатура для шага "Имя" (обычная отмена)
name_cancel_kb = types.ReplyKeyboardMarkup(
    keyboard=[[types.KeyboardButton(text="/cancel")]],
    resize_keyboard=True
)

# Клавиатура для шага "Телефон" (кнопка контакта + отмена)
phone_kb = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="📱 Поделиться контактом", request_contact=True)],
        [types.KeyboardButton(text="/cancel")]
    ],
    resize_keyboard=True
)

# Inline-клавиатура для выбора направления
direction_kb = types.InlineKeyboardMarkup(
    inline_keyboard=[
        [types.InlineKeyboardButton(text="IT", callback_data="dir_it")],
        [types.InlineKeyboardButton(text="Дизайн", callback_data="dir_design")],
        [types.InlineKeyboardButton(text="Маркетинг", callback_data="dir_marketing")],
        [types.InlineKeyboardButton(text="Другое", callback_data="dir_other")]
    ]
)

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.set_state(Form.name)
    await message.answer(
        "👋 Здравствуйте! Давайте заполним анкету.\n\n"
        "Шаг 1 из 4: Введите ваше имя:",
        reply_markup=name_cancel_kb
    )

# Команда /cancel (работает на любом шаге)
@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Заполнение анкеты отменено.\n"
        "Нажмите /start, чтобы начать заново.",
        reply_markup=types.ReplyKeyboardRemove()
    )

# Шаг 1: получение имени
@dp.message(Form.name, F.text)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(Form.phone)
    await message.answer(
        "📞 Шаг 2 из 4: Введите ваш номер телефона.\n\n"
        "Вы можете нажать кнопку ниже, чтобы поделиться контактом, или ввести номер вручную.",
        reply_markup=phone_kb
    )

# Шаг 2: получение телефона через контакт
@dp.message(Form.phone, F.contact)
async def process_phone_contact(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data(phone=phone)
    await state.set_state(Form.direction)
    await message.answer(
        "💼 Шаг 3 из 4: Выберите направление работы:",
        reply_markup=direction_kb
    )

# Шаг 2: получение телефона вручную (текстом)
@dp.message(Form.phone, F.text)
async def process_phone_text(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    await state.update_data(phone=phone)
    await state.set_state(Form.direction)
    await message.answer(
        "💼 Шаг 3 из 4: Выберите направление работы:",
        reply_markup=direction_kb
    )

# Шаг 3: обработка выбора направления (Inline-кнопки)
@dp.callback_query(Form.direction)
async def process_direction_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    direction_map = {
        "dir_it": "IT",
        "dir_design": "Дизайн",
        "dir_marketing": "Маркетинг",
        "dir_other": "Другое"
    }
    selected = direction_map.get(callback.data, "Другое")
    await state.update_data(direction=selected)
    await state.set_state(Form.day)

    # Редактируем сообщение: убираем кнопки и просим ввести день
    await callback.message.edit_text(
        f"✅ Вы выбрали направление: <b>{selected}</b>\n\n"
        "📅 Шаг 4 из 4: Введите доступный день недели:",
        parse_mode="HTML",
        reply_markup=None
    )

# Шаг 4: получение дня недели и завершение
@dp.message(Form.day, F.text)
async def process_day(message: types.Message, state: FSMContext):
    await state.update_data(day=message.text.strip())
    data = await state.get_data()
    await state.clear()

    # Короткое сообщение соискателю
    await message.answer(
        "✅ Спасибо! Ваша анкета отправлена.",
        reply_markup=types.ReplyKeyboardRemove()
    )

    # Формирование красивой анкеты для администратора
    admin_text = (
        "📋 <b>Новая анкета</b>\n\n"
        f"👤 <b>Имя:</b> {data['name']}\n"
        f"📞 <b>Телефон:</b> {data['phone']}\n"
        f"💼 <b>Направление:</b> {data['direction']}\n"
        f"📅 <b>Доступный день:</b> {data['day']}\n"
        f"🆔 <b>User ID:</b> <code>{message.from_user.id}</code>"
    )

    # Отправка администратору
    try:
        await bot.send_message(
            ADMIN_ID,
            admin_text,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Ошибка отправки админу: {e}")

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
