import os
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# Получаем токен из настроек Railway
TOKEN = os.getenv('BOT_TOKEN')

if not TOKEN:
    print("❌ Ошибка: Переменная BOT_TOKEN не найдена на сервере Railway!")
    sys.exit(1)

# Инициализируем бота, диспетчер и память для хранения шагов анкеты
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Определяем шаги нашей анкеты вакансии
class Form(StatesGroup):
    name = State()       # Шаг 1: Имя
    phone = State()      # Шаг 2: Номер телефона
    direction = State()  # Шаг 3: Направление работы
    day = State()        # Шаг 4: Доступный день

# Команда /start запускает анкетирование
@dp.message_handler(commands=['start'], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish() # Сбрасываем старые состояния, если они были
    await message.reply("👋 Здравствуйте! Давайте заполним анкету на вакансию.\nВведите ваше имя и фамилию:")
    await Form.name.set() # Включаем шаг "Имя"

# Ловим ответ на шаг "Имя"
@dp.message_handler(state=Form.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(chosen_name=message.text) # Сохраняем имя
    
    await message.reply("📱 Отлично! Теперь введите ваш контактный номер телефона:")
    await Form.phone.set() # Переходим к шагу "Телефон"

# Ловим ответ на шаг "Телефон"
@dp.message_handler(state=Form.phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(chosen_phone=message.text) # Сохраняем телефон
    
    await message.reply("⚙️ Укажите интересующее вас направление работы (например: Разработчик, Дизайнер, Администратор):")
    await Form.direction.set() # Переходим к шагу "Направление"

# Ловим ответ на шаг "Направление"
@dp.message_handler(state=Form.direction)
async def process_direction(message: types.Message, state: FSMContext):
    await state.update_data(chosen_direction=message.text) # Сохраняем направление
    
    await message.reply("📅 В какой ближайший день вы готовы приступить к работе / пройти собеседование?")
    await Form.day.set() # Переходим к шагу "День"

# Ловим финальный ответ на шаг "День" и выводим анкету
@dp.message_handler(state=Form.day)
async def process_day(message: types.Message, state: FSMContext):
    await state.update_data(chosen_day=message.text) # Сохраняем день
    
    # Вытаскиваем все сохраненные данные из памяти бота
    user_data = await state.get_data()
    
    summary = (
        "🎉 Спасибо! Ваша анкета успешно сформирована:\n\n"
        f"👤 Имя: {user_data['chosen_name']}\n"
        f"📱 Телефон: {user_data['chosen_phone']}\n"
        f"⚙️ Направление: {user_data['chosen_direction']}\n"
        f"📅 Доступный день: {user_data['chosen_day']}\n\n"
        "⏳ Наш менеджер свяжется с вами в ближайшее время!"
    )
    
    await message.reply(summary)
    await state.finish() # Очищаем состояние после завершения

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
