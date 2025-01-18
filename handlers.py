import matplotlib.pyplot as plt
from io import BytesIO
import matplotlib.pyplot as plt
import io
from aiogram.types import BufferedInputFile
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from states import UserProfile, FoodLogState, WaterLogState, ActivityLogState
from utils import calculate_water_goal, calculate_calorie_goal, get_weather, get_food_info
import asyncio

router = Router()

# Хранилище пользователей
users = {}

# Словарь калорий для разных типов активности (за 30 минут)
WORKOUT_CALORIES = {
    "Бег": 300,
    "Плавание": 250,
    "Ходьба": 150,
    "Силовая тренировка": 200,
    "Кардио тренировка": 250,
    "Сноуборд": 250,
    "Лыжи": 300,
    "Коньки": 200,
    "Ролики": 200,
}


def create_profile_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/set_profile")],
        ],
        resize_keyboard=True,
        is_persistent=True
    )


def create_main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🍴 Добавить прием пищи")],
            [KeyboardButton(text="💧 Добавить воду")],
            [KeyboardButton(text="🏋️ Добавить тренировку")],
            [KeyboardButton(text="📊 Текущий прогресс")],
            [KeyboardButton(text="📈 Графики прогресса")],
        ],
        resize_keyboard=True,
        is_persistent=True
    )


def get_user_profile(user_id: int):
    """Возвращает профиль пользователя или None, если профиль не заполнен."""
    return users.get(user_id)


async def ensure_profile(message: Message):
    """Проверяет, настроен ли профиль пользователя. Возвращает True, если да."""
    if not get_user_profile(message.from_user.id):
        await message.reply(
            "Пожалуйста, сначала настройте профиль с помощью команды /set_profile.",
            reply_markup=create_profile_keyboard()
        )
        return False
    return True


@router.message(Command("start"))
async def cmd_start(message: Message):
    user = get_user_profile(message.from_user.id)
    if user:
        await message.reply("Добро пожаловать обратно! Выберите действие:", reply_markup=create_main_menu_keyboard())
    else:
        await message.reply(
            "Добро пожаловать! Для начала работы с ботом настройте свой профиль.",
            reply_markup=create_profile_keyboard()
        )


@router.message(Command("set_profile"))
async def set_profile(message: Message, state: FSMContext):
    await message.reply("Введите ваш вес (в кг):")
    await state.set_state(UserProfile.weight)


@router.message(UserProfile.weight)
async def process_weight(message: Message, state: FSMContext):
    try:
        weight = int(message.text)
        if weight <= 0:
            raise ValueError("Вес должен быть положительным числом.")
        await state.update_data(weight=weight)
        await message.reply("Введите ваш рост (в см):")
        await state.set_state(UserProfile.height)
    except ValueError:
        await message.reply("Пожалуйста, введите корректное значение веса (в кг).")


@router.message(UserProfile.height)
async def process_height(message: Message, state: FSMContext):
    try:
        height = int(message.text)
        if height <= 0:
            raise ValueError("Рост должен быть положительным числом.")
        await state.update_data(height=height)
        await message.reply("Введите ваш возраст:")
        await state.set_state(UserProfile.age)
    except ValueError:
        await message.reply("Пожалуйста, введите корректное значение роста (в см).")


@router.message(UserProfile.age)
async def process_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        if age <= 0:
            raise ValueError("Возраст должен быть положительным числом.")
        await state.update_data(age=age)
        await message.reply("Сколько минут активности у вас в день?")
        await state.set_state(UserProfile.activity)
    except ValueError:
        await message.reply("Пожалуйста, введите корректное значение возраста.")


@router.message(UserProfile.activity)
async def process_activity(message: Message, state: FSMContext):
    try:
        activity = int(message.text)
        if activity < 0:
            raise ValueError(
                "Количество минут активности не может быть отрицательным.")
        await state.update_data(activity=activity)
        await message.reply("В каком городе вы находитесь? (на английском)")
        await state.set_state(UserProfile.city)
    except ValueError:
        await message.reply("Пожалуйста, введите корректное значение активности (в минутах).")


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
        f"Профиль настроен! Удачи на пути к здоровому образу жизни! 🌟\n"
        f"Ваша дневная норма воды: {water_goal} мл.\n"
        f"Ваша дневная норма калорий: {calorie_goal} ккал.\n\n"
        "Выберите действие:",
        reply_markup=create_main_menu_keyboard()
    )
    await state.clear()


@router.message(F.text == "📈 Графики прогресса")
async def handle_graph_request(message: Message):
    await send_progress_graphs(message)


@router.message(Command("progress_graphs"))
async def send_progress_graphs(message: Message):
    if not await ensure_profile(message):
        return  
    
    user = get_user_profile(message.from_user.id)

    water_logged = user["logged_water"]
    water_goal = user["water_goal"]
    calories_logged = user["logged_calories"]
    calorie_goal = user["calorie_goal"]

    fig, axs = plt.subplots(1, 2, figsize=(10, 5))

    # График воды
    axs[0].bar(["Выпито", "Цель"], [water_logged, water_goal], color=["blue", "lightblue"])
    axs[0].set_title("Прогресс воды")
    axs[0].set_ylabel("мл")
    axs[0].set_ylim(0, max(water_goal, water_logged) * 1.2)

    # График калорий
    axs[1].bar(["Съедено", "Цель"], [calories_logged, calorie_goal], color=["green", "lightgreen"])
    axs[1].set_title("Прогресс калорий")
    axs[1].set_ylabel("ккал")
    axs[1].set_ylim(0, max(calorie_goal, calories_logged) * 1.2)

    fig.suptitle("Ваш прогресс на сегодня", fontsize=16)
    fig.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)

    image = BufferedInputFile(buf.read(), filename="progress_graphs.png")
    await message.answer_photo(image, caption="Ваши графики прогресса 🌟")

@router.message(F.text == "💧 Добавить воду")
async def add_water(message: Message, state: FSMContext):
    if not await ensure_profile(message):
        return
    await message.reply("Введите количество воды (в мл):")
    await state.set_state(WaterLogState.amount)


@router.message(WaterLogState.amount)
async def process_water(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError(
                "Количество воды должно быть положительным числом.")
        user_id = message.from_user.id
        users[user_id]["logged_water"] += amount
        await message.reply(
            f"Вы добавили {amount} мл воды. Общий прогресс: {users[user_id]['logged_water']} / {users[user_id]['water_goal']} мл.",
            reply_markup=create_main_menu_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.reply("Пожалуйста, введите корректное значение (в мл).")


@router.message(F.text == "🍴 Добавить прием пищи")
async def add_food(message: Message, state: FSMContext):
    if not await ensure_profile(message):
        return
    await message.reply("Введите название продукта или блюда:")
    await state.set_state(FoodLogState.waiting_for_food_name)


@router.message(F.text == "🍴 Добавить прием пищи")
async def add_food(message: Message, state: FSMContext):
    if not await ensure_profile(message):
        return
    await message.reply("Введите название продукта или блюда:")
    await state.set_state(FoodLogState.waiting_for_food_name)


@router.message(FoodLogState.waiting_for_food_name)
async def process_food_name(message: Message, state: FSMContext):
    food_name = message.text

    # Получение информации о продукте (без асинхронности)
    food_info = get_food_info(food_name)

    if not food_info:
        await message.reply("Не удалось найти информацию о продукте. Попробуйте снова.")
        return

    # Сохраняем данные о продукте во временное состояние
    await state.update_data(food_name=food_info["name"], calories_per_100g=food_info["calories"])
    await message.reply(
        f"🍴 {food_info['name']} содержит {food_info['calories']} ккал на 100 г.\n"
        "Сколько грамм вы съели? Укажите число."
    )
    await state.set_state(FoodLogState.waiting_for_food_weight)


@router.message(FoodLogState.waiting_for_food_weight)
async def process_food_weight(message: Message, state: FSMContext):
    try:
        weight = int(message.text)
        if weight <= 0:
            raise ValueError("Вес должен быть положительным числом.")

        # Получаем данные из состояния
        data = await state.get_data()
        food_name = data["food_name"]
        calories_per_100g = data["calories_per_100g"]

        # Расчет калорий
        total_calories = (weight * calories_per_100g) / 100

        # Проверяем, есть ли пользователь в системе
        user = users.get(message.from_user.id, {})

        # Добавляем калории в профиль пользователя
        user["logged_calories"] += total_calories
        await message.reply(f"Записано: {total_calories:.1f} ккал ({weight} г {food_name}).")

        # Завершаем состояние
        await state.clear()

    except ValueError:
        await message.reply("Пожалуйста, укажите вес продукта в граммах (например, 150).")


@router.message(F.text == "🏋️ Добавить тренировку")
async def add_activity(message: Message, state: FSMContext):
    if not await ensure_profile(message):
        return

    # Клавиатура с типами активности
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=activity, callback_data=activity)] for activity in WORKOUT_CALORIES.keys()
        ]
    )
    await message.reply("Выберите тип тренировки:", reply_markup=keyboard)
    await state.set_state(ActivityLogState.activity_type)


@router.callback_query(ActivityLogState.activity_type)
async def process_activity_selection(callback: CallbackQuery, state: FSMContext):
    activity = callback.data
    if activity not in WORKOUT_CALORIES:
        await callback.message.reply("Выберите тип тренировки из списка.")
        return

    await state.update_data(activity_type=activity)
    await callback.message.reply("Введите длительность тренировки (в минутах):")
    await state.set_state(ActivityLogState.duration)


@router.message(ActivityLogState.duration)
async def process_activity_duration(message: Message, state: FSMContext):
    try:
        duration = int(message.text)
        if duration <= 0:
            raise ValueError(
                "Длительность тренировки должна быть положительной.")
        data = await state.get_data()
        activity_type = data["activity_type"]
        calories_burned = WORKOUT_CALORIES[activity_type] * (duration / 30)

        user_id = message.from_user.id
        users[user_id]["burned_calories"] += calories_burned

        await message.reply(
            f"Вы добавили тренировку: {activity_type} на {duration} минут.\n Сожжено {calories_burned:.0f} ккал. "
            f"Общий прогресс: сожжено {users[user_id]['burned_calories']:.0f} ккал.",
            reply_markup=create_main_menu_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.reply("Пожалуйста, введите корректное значение (в минутах).")


@router.message(F.text == "📊 Текущий прогресс")
async def view_progress(message: Message):
    if not await ensure_profile(message):
        return

    user_id = message.from_user.id
    user = users[user_id]
    progress_message = (
        f"Ваш текущий прогресс:\n"
        f"💧 Вода: {user['logged_water']} / {user['water_goal']} мл\n"
        f"🍴 Калории: {user['logged_calories']} / {user['calorie_goal']} ккал\n"
        f"🏋️ Сожжено калорий: {user['burned_calories']:.0f} ккал"
    )
    await message.reply(progress_message, reply_markup=create_main_menu_keyboard())


def setup_handlers(dp):
    dp.include_router(router)
