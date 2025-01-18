import aiohttp
import requests
from config import API_KEY


async def get_weather(city):
    url = f"http://api.weatherapi.com/v1/current.json?key={API_KEY}&q={city}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data["current"]["temp_c"]
    return 20  # если вдруг не удалось вернуть температуру, вернем 20 градусов


def get_food_info(product_name):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&search_terms={product_name}&json=true"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        products = data.get('products', [])
        if products:
            first_product = products[0]
            return {
                'name': first_product.get('product_name', 'Неизвестно'),
                'calories': first_product.get('nutriments', {}).get('energy-kcal_100g', 0)
            }
    return None


def calculate_water_goal(weight, activity, temperature):
    base = weight * 30
    extra_activity = (activity // 30) * 500
    extra_temp = 500 if temperature > 25 else 0
    return base + extra_activity + extra_temp


def calculate_calorie_goal(weight, height, age, activity):
    return 10 * weight + 6.25 * height - 5 * age + activity * 5
