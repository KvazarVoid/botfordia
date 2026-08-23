from vkbottle.bot import Bot
from vkbottle import API
from collections import defaultdict
from vkbottle import PhotoMessageUploader   
import random
import re
import ssl
import certifi
import os
import aiohttp
import gspread
from pilmoji import Pilmoji
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
from urllib.request import urlopen
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
from google.oauth2.service_account import Credentials
import vkbottle

TOKEN = os.getenv("TOKEN")
TAGS_CHAT_ID = 2000000004
STATS_FILE = "/app/data/messages_stats.json"
tracked_tags = set()
last_tags_update = 0
TAGS_UPDATE_INTERVAL = 6 * 60 * 60
BACKGROUND_PATH = "/app/data/quote_background.jpg"
waiting_for_background = set()

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
photo_uploader = PhotoMessageUploader(bot.api)
if os.path.exists("credentials.json"):
    gc = gspread.service_account(filename="credentials.json")
else:
    creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    gc = gspread.authorize(creds)
spreadsheet = gc.open_by_key("139vYcH0C77e1sOWMr68G125__J8QevYXCu_r3LegCtM")

sheet = spreadsheet.sheet1
technical_sheet = spreadsheet.worksheet("Технический")

print("БОТ ЗАПУЩЕН")

def update_tracked_tags():
    global tracked_tags, last_tags_update

    tags = sheet.col_values(1)[1:]

    tracked_tags = {
        tag.strip().lower()
        for tag in tags
        if tag.strip()
    }

    last_tags_update = datetime.now().timestamp()

def get_tracked_tags():
    global last_tags_update

    now = datetime.now().timestamp()

    if not tracked_tags or now - last_tags_update >= TAGS_UPDATE_INTERVAL:
        update_tracked_tags()

    return tracked_tags

def record_message(message):
    if message.peer_id != TAGS_CHAT_ID:
        return

    text = message.text or ""
    text_lower = text.lower()

    tags = get_tracked_tags()

    found_tags = [
        tag for tag in tags
        if tag in text_lower
    ]

    # Нет отслеживаемого тега — не записываем
    if not found_tags:
        return

    stats = load_message_stats()

    stats.append({
        "time": message.date.timestamp(),
        "user_id": message.from_id,
        "tags": found_tags
    })

    # Храним историю за год
    year_ago = (datetime.now() - timedelta(days=365)).timestamp()

    stats = [
        item for item in stats
        if item["time"] >= year_ago
    ]

    save_message_stats(stats)

def get_message_statistics(period):
    stats = load_message_stats()

    now = datetime.now()
    now_timestamp = now.timestamp()

    periods = {
        "день": 1,
        "неделю": 7,
        "месяц": 30,
        "год": 365
    }

    days = periods[period]
    start = now - timedelta(days=days)
    start_timestamp = start.timestamp()

    # Оставляем только сообщения за нужный период
    period_stats = [
        item for item in stats
        if item["time"] >= start_timestamp
    ]

    # Считаем сообщения по авторам
    author_counts = {}

    for item in period_stats:
        user_id = str(item["user_id"])
        author_counts[user_id] = author_counts.get(user_id, 0) + 1

    # Самые активные сверху
    author_counts = dict(
        sorted(
            author_counts.items(),
            key=lambda item: item[1],
            reverse=True
        )
    )

    return start, now, len(period_stats), author_counts
#Обработчик цитат
def create_quote_image(
    avatar_url,
    user_name,
    quote_date,
    quote_text,
):
    from io import BytesIO
    from PIL import Image

    test_image = Image.new("RGB", (1200, 500), "white")
    image = BytesIO()
    test_image.save(image, format="PNG")
    image.seek(0)
    image.name = "quote.png"
    print("AVATAR:", repr(avatar_url))
    print("SIZE:", len(image.getvalue()))
    # ============================================================
    # НАСТРОЙКИ ВНЕШНЕГО ВИДА
    # ============================================================

    # --- Размер карточки ---
    WIDTH = 1200
    PADDING = 30

    # --- Фон ---
    # Путь к картинке-фону в Railway Volume
    BACKGROUND_PATH = "/app/data/quote_background.jpg"

    BACKGROUND_COLOR = "white"

    # Насколько затемнять фон
    # 0 = не затемнять
    # 255 = полностью чёрный
    BACKGROUND_DARKNESS = 126
    MIN_HEIGHT = 500

    # --- Аватар ---
    AVATAR_SIZE = 140
    AVATAR_TO_NAME_GAP = 20

    # --- Размеры шрифтов ---
    NAME_SIZE = 42
    DATE_SIZE = 28
    TEXT_SIZE = 52

    # --- Вертикальные расстояния ---
    NAME_TOP_OFFSET = 20
    DATE_GAP = 55
    TEXT_TOP_GAP = 20

    # --- Текст цитаты ---
    LINE_HEIGHT = 65

    # --- Цвета ---
    NAME_COLOR = "white"
    DATE_COLOR = "#FFFFFF"
    TEXT_COLOR = "white"

    # --- Шрифт ---
    FONT_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "fonts",
        "NotoSans_Condensed-Regular.ttf"
    )

    # ============================================================
    # ГЕНЕРАЦИЯ ШРИФТОВ
    # ============================================================

    print("FONT_PATH:", FONT_PATH)
    print("FONT EXISTS:", os.path.exists(FONT_PATH))

    name_font = ImageFont.truetype(
        FONT_PATH,
        NAME_SIZE
    )

    date_font = ImageFont.truetype(
        FONT_PATH,
        DATE_SIZE
    )

    text_font = ImageFont.truetype(
        FONT_PATH,
        TEXT_SIZE
    )

    text_width = WIDTH - PADDING * 2

    # ============================================================
    # ПЕРЕНОС ТЕКСТА
    # ============================================================

    def wrap_text(text, font, max_width):
        lines = []

        # Обрабатываем каждую строку отдельно,
        # чтобы сохранять переносы строк из сообщения
        for paragraph in text.splitlines():

            # Пустая строка = настоящий абзац
            if not paragraph.strip():
                lines.append("")
                continue

            words = paragraph.split()
            current_line = ""

            for word in words:
                test_line = (
                    word
                    if not current_line
                    else current_line + " " + word
                )

                bbox = font.getbbox(test_line)
                line_width = bbox[2] - bbox[0]

                if line_width <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)

                    current_line = word

            if current_line:
                lines.append(current_line)
        return lines

    # ============================================================
    # ТЕКСТ
    # ============================================================

    if not quote_text.strip():
        quote_text = "[сообщение без текста]"

    text_lines = wrap_text(
        quote_text,
        text_font,
        text_width
    )

    MIN_HEIGHT = 500

    text_height = len(text_lines) * LINE_HEIGHT

    height = max(
        MIN_HEIGHT,
        PADDING
        + AVATAR_SIZE
        + TEXT_TOP_GAP
        + text_height
        + PADDING
    )

    # ============================================================
    # ФОН
    # ============================================================

    if BACKGROUND_PATH:
        background = Image.open(
            BACKGROUND_PATH
        ).convert("RGB")

        print("WIDTH:", WIDTH, type(WIDTH))
        print("HEIGHT:", height, type(height))

        background = ImageOps.fit(
            background,
            (WIDTH, height),
            method=Image.Resampling.LANCZOS
        )

        image = background

        # Затемнение фона, чтобы текст оставался читаемым
        overlay = Image.new(
            "RGB",
            (WIDTH, height),
            "black"
        )

        image = Image.blend(
            image,
            overlay,
            BACKGROUND_DARKNESS / 255
        )

    else:
        image = Image.new(
            "RGB",
            (WIDTH, height),
            BACKGROUND_COLOR
        )

    draw = ImageDraw.Draw(image)

    # ============================================================
    # АВАТАР
    # ============================================================

    try:
        avatar_data = urlopen(
            avatar_url,
            timeout=10
        ).read()

        avatar = Image.open(
            BytesIO(avatar_data)
        ).convert("RGB")

        avatar = avatar.resize(
            (AVATAR_SIZE, AVATAR_SIZE),
            Image.Resampling.LANCZOS
        )

        mask = Image.new(
            "L",
            (AVATAR_SIZE, AVATAR_SIZE),
            0
        )

        mask_draw = ImageDraw.Draw(mask)

        mask_draw.ellipse(
            (0, 0, AVATAR_SIZE, AVATAR_SIZE),
            fill=255
        )

        image.paste(
            avatar,
            (PADDING, PADDING),
            mask
        )

    except Exception as e:
        print(f"Ошибка загрузки аватарки: {e}")

    # ============================================================
    # ИМЯ
    # ============================================================

    name_x = (
        PADDING
        + AVATAR_SIZE
        + AVATAR_TO_NAME_GAP
    )

    name_y = (
        PADDING
        + NAME_TOP_OFFSET
    )

    with Pilmoji(image) as pilmoji:
        pilmoji.text(
            (name_x, name_y),
            user_name,
            fill=NAME_COLOR,
            font=name_font
        )

    # ============================================================
    # ДАТА
    # ============================================================

    date_x = name_x

    date_y = (
        name_y
        + DATE_GAP
    )

    with Pilmoji(image) as pilmoji:
        pilmoji.text(
            (date_x, date_y),
            quote_date.strftime("%d.%m.%Y %H:%M"),
            fill=DATE_COLOR,
            font=date_font
        )

    # ============================================================
    # ТЕКСТ ЦИТАТЫ
    # ============================================================
    # Высота области, в которой размещаем цитату
    text_area_top = (
        PADDING
        + AVATAR_SIZE
        + TEXT_TOP_GAP
    )

    text_area_bottom = height - PADDING

    text_area_height = (
        text_area_bottom - text_area_top
    )

    # Общая высота всех строк
    total_text_height = len(text_lines) * LINE_HEIGHT

    # Центрируем цитату по вертикали
    text_y = (
        text_area_top
        + (text_area_height - total_text_height) / 2
    )

    for line in text_lines:
        # Центрируем каждую строку по горизонтали
        bbox = draw.textbbox(
            (0, 0),
            line,
            font=text_font
        )

        line_width = bbox[2] - bbox[0]

        text_x = (
            WIDTH - line_width
        ) / 2

        draw.text(
            (text_x, text_y),
            line,
            font=text_font,
            fill=TEXT_COLOR
        )

        text_y += LINE_HEIGHT


    # ============================================================
    # СОХРАНЕНИЕ В ПАМЯТЬ
    # ============================================================

    output = BytesIO()

    image.save(
        output,
        format="PNG"
    )

    output.seek(0)
    output.name = "quote.png"

    return output

@bot.on.message(text="/id")
async def get_chat_id(message):
    await message.answer(
        f"peer_id: {message.peer_id}\n"
        f"conversation_message_id: {message.conversation_message_id}"
    )

async def get_ping(message, api):
    reply = message.reply_message

    if reply:
        user_id = reply.from_id
    else:
        user_id = message.from_id

    user = await api.users.get(user_ids=user_id)
    name = f"{user[0].first_name} {user[0].last_name}"

    return f"[id{user_id}|{name}]"

async def get_user_tag(user_id):
    users = await api.users.get(
        user_ids=[user_id],
        fields=["screen_name"]
    )

    if not users:
        return None

    screen_name = users[0].screen_name

    if not screen_name:
        return None

    return f"@{screen_name}"

async def update_player_response(message):
    player_tag = await get_user_tag(message.from_id)

    print("ТЕГ ИГРОКА:", player_tag)

    if not player_tag:
        return

    # Ищем теги именно в сообщении игрока
    message_tags = re.findall(r"#[A-Za-zА-Яа-яЁё0-9_]+", message.text or "")

    print("ТЕГИ В СООБЩЕНИИ ИГРОКА:", message_tags)

    if not message_tags:
        return

    values = technical_sheet.get_all_values()

    response_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    for row_index, row in enumerate(values[1:], start=2):
        if len(row) < 4:
            continue

        tag = row[0].strip()
        player = row[1].strip()
        admin_post = row[2].strip()
        player_post = row[3].strip()

        print(
            "ПРОВЕРКА СТРОКИ:",
            tag,
            player,
            admin_post,
            player_post
        )

        # Этот тег не указан в сообщении игрока
        if tag not in message_tags:
            print("ПРОПУСК: неверный тег")
            continue

        if player != player_tag:
            print("ПРОПУСК: неверный игрок")
            continue

        if not admin_post:
            print("ПРОПУСК: нет поста админа")
            continue

        if player_post:
            print("ПРОПУСК: игрок уже ответил")
            continue

        technical_sheet.update_cell(
            row_index,
            4,
            response_time
        )

        print(
            f"Игрок {player_tag} ответил "
            f"в ветке {tag}: {response_time}"
        )

def parse_players(user_text):
    """
    Получает содержимое C и возвращает список VK-тегов игроков.
    Например:
    '@ivan, @petr'
    -> ['@ivan', '@petr']
    """
    return re.findall(r"@[A-Za-zА-Яа-яЁё0-9_.]+", user_text or "")


def sync_technical_tag(tag, players, admin_post_time):
    """
    Синхронизирует игроков тега с листом 'Технический'
    и записывает новый пост админа.
    """
    values = technical_sheet.get_all_values()

    existing_rows = {}

    for row_index, row in enumerate(values[1:], start=2):
        if len(row) < 2:
            continue

        row_tag = row[0].strip()
        player = row[1].strip()

        if row_tag == tag and player:
            existing_rows[player] = row_index

    for player in players:
        if player in existing_rows:
            row = existing_rows[player]

            # Новый пост админа:
            # обновляем время и обязательно очищаем старый ответ игрока.
            technical_sheet.update(
                f"C{row}:D{row}",
                [[admin_post_time, ""]],
            )

        else:
            technical_sheet.append_row(
                [tag, player, admin_post_time, ""],
                value_input_option="USER_ENTERED"
            )

def get_admin_data():
    values = sheet.get_all_values()

    admin_ids = set()
    admin_tags = {}

    for row in values[1:]:
        if len(row) < 6:
            continue

        tag = row[0].strip()
        admin = row[5].strip()

        if not admin:
            continue

        try:
            admin_id = int(admin)
        except ValueError:
            continue

        admin_ids.add(admin_id)

        if tag:
            admin_tags.setdefault(admin_id, []).append(tag)

    return admin_ids, admin_tags

def update_sheet(text, admin_id):
    tags = re.findall(r"#[A-Za-zА-Яа-яЁё0-9_]+", text)

    print("Найдены теги:", tags)

    if not tags:
        return

    values = sheet.col_values(1)[1:]  # A, начиная со второй строки
    admin_values = sheet.col_values(6)[1:]  # F — админы

    today = datetime.now().strftime("%d.%m.%Y")
    admin_post_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    for tag in tags:
        for row, value in enumerate(values, start=2):
            if value != tag:
                continue
            row_admin = admin_values[row - 2].strip()

            if row_admin != str(admin_id):
                print(
                    f"Тег {tag} принадлежит админу {row_admin}, "
                    f"а сообщение пришло от {admin_id}"
                )
                continue

            print(f"Обновляю строку {row}: {tag}")

            # Старая система дедлайнов
            sheet.update_cell(row, 4, today)

            # Получаем игроков из C
            player_text = sheet.cell(row, 3).value
            players = parse_players(player_text)

            print(f"Игроки для {tag}: {players}")

            # Обновляем технический лист
            sync_technical_tag(
                tag,
                players,
                admin_post_time
            )
def days_text(days):
    if days % 10 == 1 and days % 100 != 11:
        return f"{days} день"
    elif days % 10 in (2, 3, 4) and not (12 <= days % 100 <= 14):
        return f"{days} дня"
    else:
        return f"{days} дней"
    
def all_players_answered(tag, values):
    found_players = False

    for row in values[1:]:
        if len(row) < 4:
            continue

        row_tag = row[0].strip()
        admin_post = row[2].strip()
        player_post = row[3].strip()

        if row_tag != tag:
            continue

        if not admin_post:
            continue

        found_players = True

        if not player_post:
            return False

        try:
            admin_time = datetime.strptime(
                admin_post,
                "%d.%m.%Y %H:%M:%S"
            )
            player_time = datetime.strptime(
                player_post,
                "%d.%m.%Y %H:%M:%S"
            )
        except ValueError:
            return False

        if player_time <= admin_time:
            return False

    return found_players
    
def get_deadlines(user_tag=None):
    # Читаем основной лист один раз
    values = sheet.get_all_values()

    # Читаем технический лист один раз
    technical_values = technical_sheet.get_all_values()

    today = datetime.now().date()
    deadlines = []

    for row in values[1:]:
        if len(row) < 4:
            continue

        tag = row[0].strip()
        user = row[2].strip()
        date_text = row[3].strip()

        if not tag or not date_text:
            continue

        # Если указан пользователь — пропускаем чужие строки
        if user_tag and user_tag not in user:
            continue

        try:
            last_date = datetime.strptime(
                date_text,
                "%d.%m.%Y"
            ).date()
        except ValueError:
            continue

        days = (today - last_date).days

        if days <= 0:
            emoji = "🟦"
            text = "сегодня"
        elif days == 1:
            emoji = "🟩"
            text = days_text(days)
        elif days == 2:
            emoji = "🟨"
            text = days_text(days)
        elif days == 3:
            emoji = "🟥"
            text = days_text(days)
        else:
            emoji = "⬛"
            text = days_text(days)

        status = " 🟢" if all_players_answered(tag, technical_values) else ""

        deadlines.append(
            (
                days,
                f"{emoji} {tag} — "
                f"{last_date.strftime('%d.%m.%Y')} "
                f"({text}){status}"
            )
        )

    deadlines.sort(reverse=True)

    return "\n".join(item[1] for item in deadlines)

def load_message_stats():
    if not os.path.exists(STATS_FILE):
        return []

    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

def load_message_stats():
    if not os.path.exists(STATS_FILE):
        return []

    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_message_stats(stats):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False)


def record_message(message):
    if message.peer_id != TAGS_CHAT_ID:
        return

    text = message.text or ""

    # Получаем существующие теги из таблицы
    tags = sheet.col_values(1)[1:]

    found_tags = []

    for tag in tags:
        tag = tag.strip()

        if tag and tag.lower() in text.lower():
            found_tags.append(tag)

    # Сообщение без отслеживаемого тега не записываем
    if not found_tags:
        return

    stats = load_message_stats()

    stats.append({
        "time": message.date.timestamp(),
        "user_id": message.from_id,
        "tags": found_tags
    })

    # Храним историю за год
    year_ago = (datetime.now() - timedelta(days=365)).timestamp()
    stats = [
        item for item in stats
        if item["time"] >= year_ago
    ]

    save_message_stats(stats)

async def upload_quote_photo(api, image, peer_id):
    server_data = await api.photos.get_messages_upload_server(
        peer_id=peer_id
    )

    upload_url = server_data.upload_url

    print("UPLOAD URL:", upload_url)

    image.seek(0)

    form = aiohttp.FormData()
    form.add_field(
        "photo",
        image,
        filename="quote.png",
        content_type="image/png"
    )

    async with aiohttp.ClientSession() as session:
        async with session.post(
            upload_url,
            data=form
        ) as response:

            raw = await response.text()

            print("UPLOAD HTTP:", response.status)
            print("UPLOAD RESPONSE:", raw)

            if response.status != 200:
                raise RuntimeError(
                    f"VK upload error {response.status}: {raw}"
                )

            upload_result = json.loads(raw)

    if not upload_result.get("photo"):
        raise RuntimeError(
            f"VK не вернул photo: {upload_result}"
        )

    return await api.photos.save_messages_photo(
        server=upload_result["server"],
        photo=upload_result["photo"],
        hash=upload_result["hash"]
    )

@bot.on.message()
async def dice(message):
    print(message.from_id)
    record_message(message)

    text = (message.text or "").lower().strip()

    # ============================================================
    # СМЕНА ФОНА ЦИТАТ
    # ============================================================

    if text == "/фон":

        admin_ids, _ = get_admin_data()

        # Только для админов
        if message.from_id not in admin_ids:
            await message.answer(
                "❌ У тебя нет прав для смены фона."
            )
            return

        # Команда должна быть ответом на сообщение
        reply = message.reply_message

        if not reply:
            await message.answer(
                "🖼 Ответь командой /фон на сообщение с картинкой."
            )
            return

        # Ищем фотографию среди вложений
        photo = None

        for attachment in reply.attachments:
            if attachment.type == "photo":
                photo = attachment.photo
                break

        if photo is None:
            await message.answer(
                "❌ В сообщении, на которое ты ответил, нет фотографии."
            )
            return

        try:
            # Берём самое большое доступное изображение
            largest_size = max(
                photo.sizes,
                key=lambda size: size.width * size.height
            )

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    largest_size.url
                ) as response:

                    if response.status != 200:
                        raise Exception(
                            f"VK вернул HTTP {response.status}"
                        )

                    image_data = await response.read()

            with open(BACKGROUND_PATH, "wb") as file:
                file.write(image_data)

            await message.answer(
                "✅ Фон цитат успешно изменён."
            )

            print(
                f"Новый фон сохранён в {BACKGROUND_PATH}"
            )

        except Exception as e:
            print(f"Ошибка сохранения фона: {e}")

            await message.answer(
                "❌ Не удалось сохранить изображение."
            )

        return
    if text == "/цитата":
        reply = message.reply_message
        print("CALLER:", message.from_id)
        print("QUOTE AUTHOR:", reply.from_id)

        if not reply:
            await message.answer(
                "❌ Команду /цитата нужно использовать ответом на сообщение."
            )
            return

        # Данные сообщения
        quote_text = reply.text or ""
        print("QUOTE TEXT:", repr(quote_text))
        user_id = reply.from_id
        quote_date = reply.date.replace(tzinfo=ZoneInfo("UTC")).astimezone(
            ZoneInfo("Europe/Kyiv")
        )
        # Получаем имя пользователя
        try:
            users = await api.users.get(
    user_ids=[user_id],
    fields=["photo_200"]
)

            if users:
                user = users[0]
                user_name = f"{user.first_name} {user.last_name}"
                avatar_url = user.photo_200
            else:
                user_name = f"VK ID {user_id}"
                avatar_url = None

        except Exception as e:
            print(f"Ошибка получения пользователя: {e}")
            user_name = f"VK ID {user_id}"

        image = create_quote_image(
            avatar_url=avatar_url,
            user_name=user_name,
            quote_date=quote_date,
            quote_text=quote_text
        )

        image.name = "quote.png"
        print("IMAGE TYPE:", type(image))
        print("=== QUOTE UPLOAD ===")
        print("PEER:", message.peer_id)
        print("IMAGE:", type(image))
        print("IMAGE NAME:", getattr(image, "name", None))
        print("IMAGE POS:", image.tell())
        print("IMAGE SIZE:", len(image.getvalue()))

        photo = await upload_quote_photo(
        api=api,
        image=image,
        peer_id=message.peer_id
        )

        await message.answer(
            attachment=photo
        )

        print(f"Автор: {user_name}")
        print(f"VK ID: {user_id}")

        return

    if text == "/обновитьтеги":
        update_tracked_tags()

        await message.answer(
            f"✅ Список тегов обновлён.\n"
            f"Загружено тегов: {len(tracked_tags)}"
        )
        return

    if text.startswith("/сообщения"):
        args = text.split()

        if len(args) != 2 or args[1] not in {"день", "неделя", "месяц", "год"}:
            await message.answer(
                "Использование:\n"
                "/сообщения день\n"
                "/сообщения неделя\n"
                "/сообщения месяц\n"
                "/сообщения год"
            )
            return

        period = args[1]

        start, end, total, author_counts = get_message_statistics(period)

        if period == "день":
            date_text = end.strftime("%d.%m.%Y")
        else:
            date_text = (
                f"{start.strftime('%d.%m.%Y')} — "
                f"{end.strftime('%d.%m.%Y')}"
            )

        text_result = (
            f"📊 Сообщения за {period}\n"
            f"{date_text}\n\n"
            f"Всего: {total}"
        )

        if author_counts:
            text_result += "\n\n👤 По авторам:"

            user_ids = [int(user_id) for user_id in author_counts.keys()]

            try:
                users = await api.users.get(user_ids=user_ids)

                names = {
                    str(user.id): f"{user.first_name} {user.last_name}"
                    for user in users
                }

            except Exception:
                names = {}

            for user_id, count in author_counts.items():
                name = names.get(user_id, f"VK {user_id}")
                text_result += f"\n{name} — {count}"
        await message.answer(text_result)
        return

    if text.startswith("/дедлайн"):
        args = text.split()

        if len(args) > 1:
            user_tag = args[1]
            result = get_deadlines(user_tag)
        else:
            result = get_deadlines()

        await message.answer(result)
        return

    admin_ids, admin_tags = get_admin_data()

    if message.from_id in admin_ids:
        own_tags = admin_tags.get(message.from_id, [])

        message_has_own_tag = any(
            tag.lower() in message.text.lower()
            for tag in own_tags
        )

        if message_has_own_tag:
            update_sheet(message.text, message.from_id)
        else:
            await update_player_response(message)
    else:
        await update_player_response(message)

    commands = {
        "/магнус": "Предатель*",
        "/пасхалко": "Пасхалко",
        "/фумо": "https://ru.wikipedia.org/wiki/Смысл_жизни",
        "/диа": "ЛУЧШАЯ РОЛЕВАЯ В МИРЕ\nЛУЧШАЯ РОЛЕВАЯ В МИРЕ\nЛУЧШАЯ РОЛЕВАЯ В МИРЕ",
        "/помощь": "/кх, /дх или /dх — бросок куба, где Х количество граней.\n/сообщения — количество сообщений за выбранный период.\n/дедлайны — дедлайны. Зелёный кружок отмечает ветки со всеми отписанными постами игроков."
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
    if text == "/тестответ":
        print("АЙЛА:", all_players_answered("#Айла"))
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
update_tracked_tags()
bot.run()
