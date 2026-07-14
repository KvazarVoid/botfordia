from vkbottle.bot import Bot
from vkbottle import API
from collections import defaultdict
import random
import re
import ssl
import certifi
import os
import gspread
from datetime import datetime
from zoneinfo import ZoneInfo

TOKEN = os.getenv("TOKEN")

ssl._create_default_https_context = lambda: ssl.create_default_context(
    cafile=certifi.where()
)


tarot_cards = {
    1: "Маг",
    2: "Верховная Жрица",
    3: "Императрица",
    4: "Император",
    5: "Иерофант",
    6: "Влюблённые",
    7: "Колесница",
    8: "Сила",
    9: "Отшельник",
    10: "Колесо Фортуны",
    11: "Справедливость",
    12: "Повешенный",
    13: "Смерть",
    14: "Умеренность",
    15: "Дьявол",
    16: "Башня",
    17: "Звезда",
    18: "Луна",
    19: "Солнце",
    20: "Суд",
    21: "Мир",
    22: "Дурак",
    23: "Младшая Аркана",
}


bot = Bot(TOKEN)
api = API(TOKEN)
gc = gspread.service_account(filename="credentials.json")
sheet = gc.open_by_key("139vYcH0C77e1sOWMr68G125__J8QevYXCu_r3LegCtM").sheet1
ALLOWED_USERS = {
    149041734,  # VK ID Алиса
}

print("БОТ ЗАПУЩЕН")


async def get_ping(message, api):
    reply = message.reply_message

    if reply:
        user_id = reply.from_id
    else:
        user_id = message.from_id

    user = await api.users.get(user_ids=user_id)
    name = user[0].first_name

    return f"[id{user_id}|{name}]"

#Хрень с таблицами
def update_sheet(text):
    tags = re.findall(r"#[A-Za-zА-Яа-яЁё0-9_]+", text)
    print(tags)
    print("Найдены теги:", tags)

    if not tags:
        return

    values = sheet.col_values(1)[1:]  # весь A, начиная со второй строки
    print("Теги из таблицы:", values)

    today = datetime.now().strftime("%d.%m.%Y")

    for tag in tags:
        for row, value in enumerate(values, start=2):
            if value == tag:
                print(f"Обновляю строку {row}: {tag}")
                sheet.update_cell(row, 4, today)

@bot.on.message()
async def dice(message):
    print(message.from_id)
    text = message.text.lower().strip()
    if message.from_id in ALLOWED_USERS:
        update_sheet(message.text)
    commands = {
        "/магнус": "Предатель*",
        "/пасхалко": "Пасхалко",
        "/фумо": "https://ru.wikipedia.org/wiki/Смысл_жизни",
        "/диа": "ЛУЧШАЯ РОЛЕВАЯ В МИРЕ\nЛУЧШАЯ РОЛЕВАЯ В МИРЕ\nЛУЧШАЯ РОЛЕВАЯ В МИРЕ",
}    
    casino_commands = {
        "/казино": "normal",
        "/деп": "deposit",
        "/slot": "slot"
    }
    if text in commands:
        await message.answer(commands[text])
        return

    mode = None

    for cmd in casino_commands:
        if text.startswith(cmd):
            mode = casino_commands[cmd]
            break

    if mode:
        parts = text.split()
        count = 1

        if len(parts) > 1 and parts[1].isdigit():
            count = int(parts[1])

        MAX_ROLLS = 50
        if count > MAX_ROLLS:
            await message.answer(f"Слишком много попыток (макс {MAX_ROLLS})")
            return

        ping = await get_ping(message, api)

        groups = defaultdict(list)

        for _ in range(count):
            roll = random.randint(1, 1000)

            if roll <= 5:
                result_text = "!!!Легендарка!!!"
            elif roll <= 25:
                result_text = "Эпическая Аркана"
            elif roll <= 100:
                result_text = "Редкая Аркана"
            elif roll <= 250:
                result_text = "Базовая Аркана"
            elif roll <= 501:
                result_text = "4 ОР"
            else:
                result_text = "Целое нихуя"

            groups[result_text].append(roll)

        output = []

        order = [
            "!!!Легендарка!!!",
            "Эпическая Аркана",
            "Редкая Аркана",
            "Базовая Аркана",
            "4 ОР",
            "Целое нихуя"
        ]

        for name in order:
            if name in groups:
                rolls = groups[name]
                output.append(
                    f"{len(rolls)}x {name} ({', '.join(map(str, rolls))})"
                )

        await message.answer(
            f"{ping}\n"
            f"Казино x{count}:\n\n" +
            "\n".join(output)
        )

        return
    if text == "/расклад":

        results = []

        rolls = random.sample(range(1, 24), 3)

        for roll in rolls:
            card = tarot_cards.get(roll, "Неизвестная карта")
            results.append(f"{roll} — {card}")
        ping = await get_ping(message, api)
        await message.answer(
            f"{ping}\n"
            f"🃏 Карты:\n" +
            "\n".join(results)
        )
        return
    if text.startswith("/смерть"):

        parts = text.split()

        # модификатор (по умолчанию 0)
        modifier = 0

        if len(parts) > 1:
            try:
                modifier = int(parts[1])
            except ValueError:
                modifier = 0

        roll = random.randint(1, 20)
        total = roll + modifier

        mod_text = f"+{modifier}" if modifier >= 0 else str(modifier)

        if total <= 20:
            result_text = "Мои соболезнования."
        elif total > 20:
            result_text = "Мать вашу, оно живёт!"
        ping = await get_ping(message, api)
        await message.answer(
            f"{ping}\n"
            f"Ухх, бля, поехали\n"
            f"Ваша судьба — {total}\n"
            f"...\n"
            f"{result_text}"
        )

        return
    text = message.text.lower().strip()

    match = re.fullmatch(r"/(\d*)(?:к|d|д)(\d+)([+-]\d+)?", text)

    if match:

        count = int(match.group(1) or 1)
        MAX_DICE = 10
        if count > MAX_DICE:
            await message.answer(f"Много хочешь (макс {MAX_DICE})")
            return
        sides = int(match.group(2))
        modifier = int(match.group(3) or 0)

        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls) + modifier

        rolls_text = " + ".join(map(str, rolls))

        mod_text = ""
        if modifier:
            sign = "+ " if modifier > 0 else ""
            mod_text = f" {sign}{modifier}"
        reply = message.reply_message

        if reply:
            user_id = reply.from_id
        else:
            user_id = message.from_id

        ping = await get_ping(message, api)

        await message.answer(
        f"{ping}\n"
        f"🎲 {count}к{sides}\n"
        f"[ {rolls_text}{mod_text} ]\n"
        f"Σ = {total}"
)
bot.run()