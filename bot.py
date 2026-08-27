import asyncio
import json
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()
SAVE_FILE = Path(__file__).parent / "applications.json"
ALLOWED_PROXY = ("socks5", "socks4", "http", "https")


def normalize_proxy(raw: str) -> str:
    raw = raw.strip().strip('"').strip("'")
    if not raw:
        return ""
    if raw.startswith("://"):
        raw = "socks5" + raw
    if "://" not in raw:
        raise SystemExit(
            "PROXY без схемы. Нужна строка целиком, например:\n"
            "  PROXY=socks5://127.0.0.1:1080\n"
            "  PROXY=http://127.0.0.1:8080\n"
            "Один IP:порт без socks5:// или http:// бот не поймёт.\n"
            f"Сейчас в .env: {raw}"
        )
    scheme = raw.split("://", 1)[0].lower()
    if scheme not in ALLOWED_PROXY:
        raise SystemExit(
            "Этот прокси боту не подходит.\n"
            "Нужен SOCKS5 или HTTP, не MTProto (tg://) и не случайная ссылка с сайта.\n"
            f"Сейчас схема: {scheme}"
        )
    return raw

DIRECTIONS = ("Рисунок", "Лепка", "Игры")
DAYS = ("Суббота", "Воскресенье")


class SignUp(StatesGroup):
    name = State()
    phone = State()
    direction = State()
    day = State()
    confirm = State()


def kb(items: tuple[str, ...]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=item)] for item in items],
        resize_keyboard=True,
    )


START_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Записаться")]],
    resize_keyboard=True,
)


def save_application(data: dict) -> None:
    rows = []
    if SAVE_FILE.exists():
        rows = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
    rows.append(data)
    SAVE_FILE.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def summary(data: dict) -> str:
    return (
        "Проверьте заявку:\n"
        f"Имя: {data['name']}\n"
        f"Телефон: {data['phone']}\n"
        f"Направление: {data['direction']}\n"
        f"День: {data['day']}"
    )


async def notify_admin(bot: Bot, text: str) -> None:
    if not ADMIN_ID.isdigit():
        print("ADMIN_ID не задан. Заявка только в applications.json")
        print(text)
        return
    await bot.send_message(int(ADMIN_ID), text)


dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Привет! Это запись на пробное занятие в «Ламповой студии».",
        reply_markup=START_KB,
    )


@dp.message(Command("id"))
async def show_id(message: Message) -> None:
    await message.answer(f"Твой Telegram id: {message.from_user.id}")


@dp.message(F.text == "Записаться")
async def begin(message: Message, state: FSMContext) -> None:
    await state.set_state(SignUp.name)
    await message.answer("Как вас зовут?", reply_markup=ReplyKeyboardRemove())


@dp.message(SignUp.name)
async def got_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Напишите имя текстом, хотя бы 2 буквы.")
        return
    await state.update_data(name=name)
    await state.set_state(SignUp.phone)
    await message.answer("Номер телефона (можно с +7):")


@dp.message(SignUp.phone)
async def got_phone(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) < 10:
        await message.answer("Похоже, это не телефон. Напишите номер ещё раз.")
        return
    await state.update_data(phone=raw)
    await state.set_state(SignUp.direction)
    await message.answer("Какое направление?", reply_markup=kb(DIRECTIONS))


@dp.message(SignUp.direction)
async def got_direction(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text not in DIRECTIONS:
        await message.answer("Нажмите одну из кнопок ниже.", reply_markup=kb(DIRECTIONS))
        return
    await state.update_data(direction=text)
    await state.set_state(SignUp.day)
    await message.answer("Какой день удобнее?", reply_markup=kb(DAYS))


@dp.message(SignUp.day)
async def got_day(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text not in DAYS:
        await message.answer("Нажмите «Суббота» или «Воскресенье».", reply_markup=kb(DAYS))
        return
    await state.update_data(day=text)
    data = await state.get_data()
    await state.set_state(SignUp.confirm)
    await message.answer(
        summary(data) + "\n\nВсё верно?",
        reply_markup=kb(("Да", "Нет")),
    )


@dp.message(SignUp.confirm, F.text == "Да")
async def confirm_yes(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    data["from_user"] = message.from_user.id if message.from_user else None
    save_application(data)
    await notify_admin(
        bot,
        "Новая заявка:\n"
        f"Имя: {data['name']}\n"
        f"Телефон: {data['phone']}\n"
        f"Направление: {data['direction']}\n"
        f"День: {data['day']}\n"
        f"Telegram id: {data['from_user']}",
    )
    await state.clear()
    await message.answer(
        "Заявка принята, вам напишут.",
        reply_markup=START_KB,
    )


@dp.message(SignUp.confirm, F.text == "Нет")
async def confirm_no(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SignUp.name)
    await message.answer("Хорошо, заполним заново. Как вас зовут?", reply_markup=ReplyKeyboardRemove())


@dp.message(SignUp.confirm)
async def confirm_other(message: Message) -> None:
    await message.answer("Нажмите «Да» или «Нет».", reply_markup=kb(("Да", "Нет")))


async def main() -> None:
    if not BOT_TOKEN or BOT_TOKEN == "сюда_токен_от_BotFather":
        raise SystemExit("Открой файл .env и вставь BOT_TOKEN от @BotFather")
    proxy = normalize_proxy(os.getenv("PROXY", ""))
    try:
        session = AiohttpSession(proxy=proxy) if proxy else AiohttpSession()
    except ValueError as exc:
        raise SystemExit(
            "PROXY написан криво. Пример: socks5://хост:порт\n"
            f"Деталь: {exc}"
        ) from exc
    bot = Bot(BOT_TOKEN, session=session)
    if proxy:
        print("Прокси включён:", proxy.split("@")[-1])
    else:
        print("Прокси нет. Если api.telegram.org не открывается — заполни PROXY в .env")
    print("Бот запущен. Остановка: Ctrl+C")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
