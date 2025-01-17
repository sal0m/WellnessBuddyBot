from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states import UserProfile
from utils import calculate_water_goal, calculate_calorie_goal, get_weather, get_food_info

router = Router()

# Хранилище пользователей
users = {}

# Команда /start
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply("Добро пожаловать в WellnessBuddyBot! Используйте /set_profile для настройки вашего профиля.")

# Команда /set_profile
@router.message(Command("set_profile"))
async def set_profile(message: Message, state: FSMContext):
    await message.reply("Введите ваш вес (в кг):")
    await state.set_state(UserProfile.weight)

@router.message(UserProfile.weight)
async def process_weight(message: Message, state: FSMContext):
    await state.update_data(weight=int(message.text))
    await message.reply("Введите ваш рост (в см):")
    await state.set_state(UserProfile.height)

@router.message(UserProfile.height)
async def process_height(message: Message, state: FSMContext):
    await state.update_data(height=int(message.text))
    await message.reply("Введите ваш возраст:")
    await state.set_state(UserProfile.age)

@router.message(UserProfile.age)
async def process_age(message: Message, state: FSMContext):
    await state.update_data(age=int(message.text))
    await message.reply("Сколько минут активности у вас в день?")
    await state.set_state(UserProfile.activity)

@router.message(UserProfile.activity)
async def process_activity(message: Message, state: FSMContext):
    await state.update_data(activity=int(message.text))
    await message.reply("В каком городе вы находитесь?")
    await state.set_state(UserProfile.city)

@router.message(UserProfile.city)
async def process_city(message: Message, state: FSMContext):
    data = await state.get_data()
    weight, height, age, activity = data["weight"], data["height"], data["age"], data["activity"]
    city = message.text

    weather = await get_weather(city)
    water_goal = calculate_water_goal(weight, activity, weather)
    calorie_goal = calculate_calorie_goal(weight, height, age, activity)

    users[message.from_user.id] = {
        "weight": weight,
        "height": height,
        "age": age,
        "activity": activity,
        "city": city,
        "water_goal": water_goal,
        "calorie_goal": calorie_goal,
        "logged_water": 0,
        "logged_calories": 0,
        "burned_calories": 0
    }

    await message.reply(
        f"Профиль настроен! 🌟\n"
        f"Ваша дневная норма воды: {water_goal} мл.\n"
        f"Ваша дневная норма калорий: {calorie_goal} ккал."
    )
    await state.clear()

# Команда /log_water
@router.message(Command("log_water"))
async def log_water(message: Message):
    try:
        amount = int(message.get_args())
        user = users.get(message.from_user.id, {})
        if not user:
            await message.reply("Пожалуйста, сначала настройте профиль с помощью команды /set_profile.")
            return
        user["logged_water"] += amount
        await message.reply(
            f"💧 Вы выпили {amount} мл воды. Осталось: {user['water_goal'] - user['logged_water']} мл."
        )
    except ValueError:
        await message.reply("Пожалуйста, укажите количество воды в миллилитрах.")

# Команда /log_food
@router.message(Command("log_food"))
async def log_food(message: Message):
    product_name = message.get_args()
    if not product_name:
        await message.reply("Пожалуйста, укажите название продукта.")
        return

    food_info = get_food_info(product_name)
    if not food_info:
        await message.reply("Не удалось найти информацию о продукте.")
        return

    await message.reply(
        f"🍴 {food_info['name']} — {food_info['calories']} ккал на 100 г.\n"
        "Сколько грамм вы съели?"
    )

# Команда /check_progress
@router.message(Command("check_progress"))
async def check_progress(message: Message):
    user = users.get(message.from_user.id, {})
    if not user:
        await message.reply("Пожалуйста, сначала настройте профиль с помощью команды /set_profile.")
        return

    await message.reply(
        f"📊 Прогресс:\n"
        f"Вода: {user['logged_water']} мл из {user['water_goal']} мл.\n"
        f"Калории: {user['logged_calories']} ккал из {user['calorie_goal']} ккал."
    )

# Функция для подключения обработчиков
def setup_handlers(dp):
    dp.include_router(router)