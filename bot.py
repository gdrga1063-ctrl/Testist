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

# Клавиатура для отмены
cancel_kb = types.ReplyKeyboardMarkup(
    keyboard=[[types.KeyboardButton(text="/cancel")]],
    resize_keyboard=True
)

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.set_state(Form.name)
    await message.answer(
        "Здравствуйте! Давайте заполним анкету.\n"
        "Введите ваше имя:",
        reply_markup=cancel_kb
    )

# Команда /cancel
@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Заполнение анкеты отменено. Нажмите /start, чтобы начать заново.",
        reply_markup=types.ReplyKeyboardRemove()
    )

# Обработка имени
@dp.message(Form.name, F.text)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Form.phone)
    await message.answer("Введите ваш номер телефона:")

# Обработка телефона
@dp.message(Form.phone, F.text)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(Form.direction)
    await message.answer("Введите направление работы (например, IT, Дизайн, Маркетинг):")

# Обработка направления
@dp.message(Form.direction, F.text)
async def process_direction(message: types.Message, state: FSMContext):
    await state.update_data(direction=message.text)
    await state.set_state(Form.day)
    await message.answer("Введите удобный день недели:")

# Обработка дня недели и завершение
@dp.message(Form.day, F.text)
async def process_day(message: types.Message, state: FSMContext):
    await state.update_data(day=message.text)
    data = await state.get_data()
    await state.clear()

    # Формирование текста анкеты
    user_info = (
        f"📋 <b>Новая анкета</b>\n\n"
        f"👤 <b>Имя:</b> {data['name']}\n"
        f"📞 <b>Телефон:</b> {data['phone']}\n"
        f"💼 <b>Направление:</b> {data['direction']}\n"
        f"📅 <b>Доступный день:</b> {data['day']}\n"
        f"🆔 <b>User ID:</b> <code>{message.from_user.id}</code>"
    )

    # Отправка пользователю
    await message.answer(
        "✅ Спасибо! Ваша анкета отправлена. Мы свяжемся с вами.",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await message.answer(user_info, parse_mode="HTML")

    # Отправка администратору
    try:
        await bot.send_message(
            ADMIN_ID,
            user_info,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Ошибка отправки админу: {e}")

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
