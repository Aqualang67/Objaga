import os
import re
from vkbottle.bot import Bot, Message
from vkbottle import Keyboard, Text, OpenLink

from verification import verify_user, get_user_block
from Database import (
    init_db,
    get_resident,
    get_registration_request,
    get_pending_requests,
    approve_registration_request,
    reject_registration_request,
    create_issue,
    count_user_issues_today,
    get_issue_recipients,
    create_feedback_message,
    get_laundry_responsible,
    create_laundry_request,
    get_pending_direct_laundry_requests,
    get_pending_pool_laundry_requests,
    move_laundry_request_to_pool,
    accept_laundry_request,
    create_market_ad,
    get_market_ad_titles,
    get_market_ad,
    get_market_ads_for_delete,
    delete_market_ad,
    get_issues_by_type,
)

API_TOKEN = os.getenv("API_KEY")

if not API_TOKEN:
    raise ValueError("Не найдена переменная окружения API_KEY")

bot = Bot(token=API_TOKEN)
init_db()

user_states = {}
user_data = {}
resident_cache = {}

CHAT_LINKS = {
    "Общежитие": "https://vk.me/join/Ef__dXCzRt1c87GjMKYfc6I1Hsi0k5EE6QA=",
    "1 этаж": "https://vk.me/join/8GpOROS5RQYA/_ZNA2_gFIIEBzcMEJwRa8I=",
    "2 левый": "https://vk.me/join/KpKYyQaYesMeMHPSs2B8lITWPVpE4kNxc1c=",
    "2 правый": "https://vk.me/join/jXjJcgP7ymCZjtcSkpIYEaX8Jz90tCrJ0s0=",
    "3 левый": "https://vk.me/join/Cjg7NHVHXZjDZHfDwJlHtZCeQeLZh0E_k3c=",
    "3 правый": "https://vk.me/join/vQhhUGWMyQ9ZlDbtoKNQNMJwe123r4xLc70=",
    "4 левый": "https://vk.me/join/LxJ4EUE90W26D6gz8SAK2H93XkQsxIyK/ps=",
    "4 правый": "https://vk.me/join/WaUYVpWsxB5HNNvNs3WO4yurgbTxY/2b59Y=",
    "5 левый": "https://vk.me/join/_dqGuz_RvceR8cHXhLn4ZIqWI1yOhJd/35g=",
    "5 правый": "https://vk.me/join/_dqGuz_RvceR8cHXhLn4ZIqWI1yOhJd/35g=",
    "Ответственные за постирочную": "https://vk.me/join/2TQL2XsBtSlefnKfk7BEALmmVjaD_4FzCYE=",
}

CHAIRMAN_IDS = {
    284114438
}

DAILY_ISSUE_LIMIT = 3

FIO_PATTERN = re.compile(r"^[А-ЯЁ][а-яё-]+(?:\s+[А-ЯЁ][а-яё-]+){1,2}$")
ROOM_PATTERN = re.compile(r"^([1-9]\d{0,2})[А-ЯЁ]?$")
TIME_PATTERN = re.compile(r"^(?:[01]?\d|2[0-3])[:.][0-5]\d$")

LAUNDRY_DIRECT_ROLE = "Ответственный по постирочной"
LAUNDRY_POOL_ROLES = {"Ответственный", "Ответственный по постирочной", "Председатель"}

reg_menu = Keyboard(inline=False)
reg_menu.add(Text("Регистрация"))

empty_menu = Keyboard(inline=False)
empty_menu.add(Text("🔙 Назад"))

faq_menu = Keyboard(inline=False)
faq_menu.add(Text("⏰ Комендантский час"))
faq_menu.add(Text("📶 Wi-Fi"))
faq_menu.row()
faq_menu.add(Text("🔙 Назад"))

services_menu = Keyboard(inline=False)
services_menu.add(Text("📝 Подать заявку"))
services_menu.add(Text("⚠️ Жалоба"))
services_menu.row()
services_menu.add(Text("🧺 Постирочная"))
services_menu.add(Text("🏪 Торговый зал"))
services_menu.row()
services_menu.add(Text("📨 Обратная связь"))
services_menu.add(Text("🔙 Назад"))

market_menu = Keyboard(inline=False)
market_menu.add(Text("➕ Разместить объявление"))
market_menu.add(Text("📋 Смотреть объявления"))
market_menu.row()
market_menu.add(Text("🗑 Удалить объявление"))
market_menu.add(Text("🔙 Назад"))

admin_menu = Keyboard(inline=False)
admin_menu.add(Text("Просмотр жалоб"))
admin_menu.add(Text("Просмотр заявок"))
admin_menu.row()
admin_menu.add(Text("Одобрение регистрации"))
admin_menu.row()
admin_menu.add(Text("🔙 Назад"))

approval_action_menu = Keyboard(inline=False)
approval_action_menu.add(Text("Одобрить"))
approval_action_menu.add(Text("Отклонить"))
approval_action_menu.row()
approval_action_menu.add(Text("🔙 Назад"))

laundry_direct_action_menu = Keyboard(inline=False)
laundry_direct_action_menu.add(Text("Принять"))
laundry_direct_action_menu.add(Text("В общий пул"))
laundry_direct_action_menu.row()
laundry_direct_action_menu.add(Text("🔙 Назад"))

laundry_pool_action_menu = Keyboard(inline=False)
laundry_pool_action_menu.add(Text("Принять"))
laundry_pool_action_menu.row()
laundry_pool_action_menu.add(Text("🔙 Назад"))

delete_ad_confirm_menu = Keyboard(inline=False)
delete_ad_confirm_menu.add(Text("Удалить"))
delete_ad_confirm_menu.add(Text("Отмена"))
delete_ad_confirm_menu.row()
delete_ad_confirm_menu.add(Text("🔙 Назад"))


def resident_to_dict(resident):
    if resident is None:
        return None

    return {
        "full_name": resident[0],
        "room_number": resident[1],
        "study_group": resident[2],
        "phone": resident[3],
        "user_block": resident[4],
        "job": resident[5],
    }


def request_to_dict(request_row):
    if request_row is None:
        return None

    return {
        "id": request_row[0],
        "vk_id": request_row[1],
        "full_name": request_row[2],
        "room_number": request_row[3],
        "study_group": request_row[4],
        "user_block": request_row[5],
        "status": request_row[6],
        "created_at": request_row[7],
    }


def laundry_request_to_dict(row):
    if row is None:
        return None

    return {
        "id": row[0],
        "creator_vk_id": row[1],
        "creator_name": row[2],
        "room_number": row[3],
        "user_block": row[4],
        "requested_time": row[5],
        "status": row[6],
        "assigned_to": row[7],
        "created_at": row[8],
    }


def market_ad_to_dict(row):
    if row is None:
        return None

    return {
        "id": row[0],
        "creator_vk_id": row[1],
        "creator_name": row[2],
        "room_number": row[3],
        "user_block": row[4],
        "title": row[5],
        "description": row[6],
        "contacts": row[7],
        "status": row[8],
        "created_at": row[9],
    }


def get_roles(resident):
    if resident is None or not resident.get("job"):
        return []
    return [item.strip() for item in resident["job"].split(",") if item.strip()]


def has_role(resident, *roles):
    resident_roles = set(get_roles(resident))
    return any(role in resident_roles for role in roles)


def is_private_message(message: Message) -> bool:
    return message.peer_id == message.from_id


async def require_private_message(message: Message) -> bool:
    if not is_private_message(message):
        return False
    return True


def can_see_chats(resident):
    if resident is None:
        return False

    if has_role(resident, "Администрация") and not has_role(resident, "Председатель"):
        return False

    return True


def load_resident(vk_id: int):
    resident = resident_to_dict(get_resident(vk_id))

    if resident is None:
        resident_cache.pop(vk_id, None)
        return None

    resident_cache[vk_id] = resident
    return resident


def get_current_resident(vk_id: int):
    return resident_cache.get(vk_id) or load_resident(vk_id)


def get_current_request(vk_id: int):
    return request_to_dict(get_registration_request(vk_id))


def is_management(vk_id: int, resident=None):
    if vk_id in CHAIRMAN_IDS:
        return True

    if resident is None:
        resident = get_current_resident(vk_id)

    if resident is None:
        return False

    return has_role(resident, "Председатель", "Администрация")


def is_laundry_direct_manager(vk_id: int, resident=None):
    if resident is None:
        resident = get_current_resident(vk_id)

    if resident is None:
        return False

    return has_role(resident, LAUNDRY_DIRECT_ROLE)


def is_laundry_pool_manager(vk_id: int, resident=None):
    if resident is None:
        resident = get_current_resident(vk_id)

    if resident is None:
        return False

    if vk_id in CHAIRMAN_IDS:
        return True

    return has_role(resident, *LAUNDRY_POOL_ROLES)


def get_available_chat_names(resident):
    if resident is None:
        return []

    if not can_see_chats(resident):
        return []

    chats = ["Общежитие"]
    user_block = resident["user_block"]

    if user_block and user_block in CHAT_LINKS and user_block not in chats:
        chats.append(user_block)

    if has_role(resident, "Староста", "Ответственный", "Председатель", "Ответственный по постирочной"):
        chats.append("Ответственные за постирочную")

    return [chat for chat in chats if chat in CHAT_LINKS]


def build_chats_menu(resident):
    keyboard = Keyboard(one_time=False, inline=False)

    for chat_name in get_available_chat_names(resident):
        keyboard.add(OpenLink(label=chat_name, link=CHAT_LINKS[chat_name]))
        keyboard.row()

    keyboard.add(Text("🔙 Назад"))
    return keyboard


def build_main_menu_for_user(vk_id: int, resident):
    keyboard = Keyboard(inline=False)
    keyboard.add(Text("📋 FAQ"))
    keyboard.add(Text("📞 Контакты"))
    keyboard.row()
    keyboard.add(Text("🛠️ Сервисы и обращения"))

    if can_see_chats(resident):
        keyboard.add(Text("💬 Чаты"))

    if is_management(vk_id, resident):
        keyboard.row()
        keyboard.add(Text("👑 Администрирование"))

    if is_laundry_direct_manager(vk_id, resident) or is_laundry_pool_manager(vk_id, resident):
        keyboard.row()
        keyboard.add(Text("🧺 Управление постирочной"))

    return keyboard


def issue_type_label(issue_type: str):
    if issue_type == "request":
        return "Заявка"
    if issue_type == "complaint":
        return "Жалоба"
    return "Обращение"


def build_vk_profile_link(vk_id: int):
    return f"https://vk.com/id{vk_id}"


async def safe_notify(peer_id: int, text: str):
    try:
        await bot.api.messages.send(peer_id=peer_id, message=text, random_id=0)
    except Exception as e:
        print(f"Ошибка уведомления {peer_id}: {e}")


async def safe_notify_user(vk_id: int, text: str):
    if not vk_id:
        return
    await safe_notify(vk_id, text)


async def send_issue_notifications(sender_vk_id: int, resident: dict, issue_id: int, issue_type: str, issue_text: str):
    recipients = get_issue_recipients(resident["user_block"])
    sent_to = set()

    notification_text = (
        f"{issue_type_label(issue_type)} #{issue_id}\n"
        f"Отправитель: {resident['full_name']}\n"
        f"Комната: {resident['room_number']}\n"
        f"Группа: {resident['study_group']}\n"
        f"Крыло/этаж: {resident['user_block']}\n"
        f"Текст: {issue_text}\n"
        f"Профиль: {build_vk_profile_link(sender_vk_id)}"
    )

    for recipient_vk_id, recipient_name, recipient_job, recipient_block in recipients:
        if recipient_vk_id == sender_vk_id:
            continue
        if recipient_vk_id in sent_to:
            continue

        await safe_notify_user(recipient_vk_id, notification_text)
        sent_to.add(recipient_vk_id)


async def submit_issue(message: Message, resident: dict, issue_type: str, issue_text: str):
    today_count = count_user_issues_today(message.from_id)

    if today_count >= DAILY_ISSUE_LIMIT:
        await message.answer(
            f"Лимит обращений на сегодня исчерпан. Можно отправить не больше {DAILY_ISSUE_LIMIT} обращений в сутки."
        )
        await show_main_menu(message)
        return

    issue_id = create_issue(
        creator_vk_id=message.from_id,
        creator_name=resident["full_name"],
        room_number=resident["room_number"],
        user_block=resident["user_block"],
        issue_type=issue_type,
        issue_text=issue_text,
    )

    if not issue_id:
        await message.answer("Не удалось сохранить обращение. Попробуй позже.")
        await show_main_menu(message)
        return

    await send_issue_notifications(
        sender_vk_id=message.from_id,
        resident=resident,
        issue_id=issue_id,
        issue_type=issue_type,
        issue_text=issue_text,
    )

    await message.answer(
        f"{issue_type_label(issue_type)} отправлена. Её получили староста или ответственный по блоку и руководство."
    )
    await show_main_menu(message)


async def notify_laundry_acceptance(accepted_by_vk_id: int, selected_request: dict):
    acceptor = get_current_resident(accepted_by_vk_id)
    acceptor_name = acceptor["full_name"] if acceptor else f"id{accepted_by_vk_id}"
    acceptor_room = acceptor["room_number"] if acceptor else "неизвестно"

    await safe_notify_user(
        selected_request["creator_vk_id"],
        f"Твоя заявка на постирочную #{selected_request['id']} принята.\n"
        f"Кто принял: {acceptor_name}\n"
        f"Комната: {acceptor_room}\n"
        f"VK: {build_vk_profile_link(accepted_by_vk_id)}"
    )

    await safe_notify_user(
        accepted_by_vk_id,
        f"Ты принял заявку на постирочную #{selected_request['id']}.\n"
        f"Кто подал: {selected_request['creator_name']}\n"
        f"Комната: {selected_request['room_number']}\n"
        f"VK: {build_vk_profile_link(selected_request['creator_vk_id'])}\n"
        f"Время: {selected_request['requested_time']}"
    )


async def show_main_menu(message: Message):
    resident = get_current_resident(message.from_id)

    await message.answer(
        "Привет! Я бот общежития. Чем могу помочь?",
        keyboard=build_main_menu_for_user(message.from_id, resident)
    )


async def restore_menu_if_needed(message: Message):
    resident = load_resident(message.from_id)

    if resident is not None:
        user_states.pop(message.peer_id, None)
        user_data.pop(message.peer_id, None)
        await show_main_menu(message)
        return True

    request = get_current_request(message.from_id)
    if request is not None and request["status"] == "pending":
        await message.answer(
            "Твоя заявка уже отправлена руководству. Дождись подтверждения.",
            keyboard=reg_menu
        )
        return True

    return False


async def start_registration(message: Message):
    user_states[message.peer_id] = "waiting_reg_full_name"
    user_data.pop(message.peer_id, None)

    await message.answer(
        "Введите полное ФИО.\nНапример: Иванов Иван Иванович",
        keyboard=reg_menu
    )


async def handle_unapproved_user(message: Message):
    request = get_current_request(message.from_id)

    if request is not None and request["status"] == "pending":
        await message.answer(
            "Твоя заявка уже отправлена руководству. Дождись подтверждения.",
            keyboard=reg_menu
        )
        return

    if request is not None and request["status"] == "rejected":
        await message.answer(
            "Предыдущая заявка была отклонена. Заполни регистрацию заново.",
            keyboard=reg_menu
        )

    await start_registration(message)


async def require_resident(message: Message):
    resident = get_current_resident(message.from_id)

    if resident is None:
        await handle_unapproved_user(message)
        return None

    return resident


async def require_management(message: Message):
    resident = await require_resident(message)
    if resident is None:
        return None

    if not is_management(message.from_id, resident):
        await message.answer("У тебя нет доступа к этому разделу.")
        return None

    return resident


@bot.on.message(text=["Начать", "start", "меню", "🔙 Назад"])
async def start_handler(message: Message):
    if not await require_private_message(message):
        return

    state = user_states.get(message.peer_id)

    if state in ("waiting_reg_full_name", "waiting_reg_room", "waiting_reg_group"):
        await message.answer("Сначала заверши регистрацию.")
        return

    user_states.pop(message.peer_id, None)
    user_data.pop(message.peer_id, None)

    resident = load_resident(message.from_id)

    if resident is None:
        await handle_unapproved_user(message)
        return

    await show_main_menu(message)


@bot.on.message(text="Регистрация")
async def reg_start(message: Message):
    if not await require_private_message(message):
        return

    resident = get_current_resident(message.from_id)

    if resident is not None:
        await message.answer("Ты уже зарегистрирован.")
        await show_main_menu(message)
        return

    request = get_current_request(message.from_id)
    if request is not None and request["status"] == "pending":
        await message.answer("Твоя заявка уже отправлена руководству. Дождись подтверждения.")
        return

    user_states[message.peer_id] = "waiting_reg_full_name"
    user_data.pop(message.peer_id, None)

    await message.answer(
        "Введите полное ФИО.\nНапример: Иванов Иван Иванович",
        keyboard=reg_menu
    )


@bot.on.message(text="📋 FAQ")
async def faq_handler(message: Message):
    if not await require_private_message(message):
        return

    resident = await require_resident(message)
    if resident is None:
        return

    await message.answer("Выбери тему:", keyboard=faq_menu)


@bot.on.message(text="⏰ Комендантский час")
async def komendant_handler(message: Message):
    if not await require_private_message(message):
        return

    resident = await require_resident(message)
    if resident is None:
        return

    await message.answer("Комендантский час с 23:00 до 06:00. Вход и выход только по пропуску.")


@bot.on.message(text="📶 Wi-Fi")
async def wifi_handler(message: Message):
    if not await require_private_message(message):
        return

    resident = await require_resident(message)
    if resident is None:
        return

    await message.answer("Сеть: DormWiFi. Пароль указан на стенде у вахты. При сбоях используй раздел сервисов и обращений.")


@bot.on.message(text="📞 Контакты")
async def contacts_handler(message: Message):
    if not await require_private_message(message):
        return

    resident = await require_resident(message)
    if resident is None:
        return

    await message.answer(
        "Комендант: +7 (XXX) XXX-XX-XX\n"
        "Зав. общежитием: +7 (XXX) XXX-XX-XX\n"
        "Председатель студсовета: +7 (900) 015-45-94"
    )


@bot.on.message(text="🛠️ Сервисы и обращения")
async def services_handler(message: Message):
    if not await require_private_message(message):
        return

    resident = await require_resident(message)
    if resident is None:
        return

    await message.answer("Выбери нужный раздел:", keyboard=services_menu)


@bot.on.message(text="📝 Подать заявку")
async def request_prompt(message: Message):
    if not await require_private_message(message):
        return

    resident = await require_resident(message)
    if resident is None:
        return

    user_states[message.peer_id] = "waiting_request"
    await message.answer(
        "Опиши проблему одним сообщением.\nНапример: 'Сломан кран в душе' или 'Не работает свет на кухне'.",
        keyboard=empty_menu
    )


@bot.on.message(text="⚠️ Жалоба")
async def complaint_prompt(message: Message):
    if not await require_private_message(message):
        return

    resident = await require_resident(message)
    if resident is None:
        return

    user_states[message.peer_id] = "waiting_complaint"
    await message.answer(
        "Опиши жалобу одним сообщением.\nНапример: 'Сильный шум ночью из 22 комнаты' или 'Кто-то курит в коридоре'.",
        keyboard=empty_menu
    )


@bot.on.message(text="🧺 Постирочная")
async def laundry_handler(message: Message):
    if not await require_private_message(message):
        return

    resident = await require_resident(message)
    if resident is None:
        return

    user_states[message.peer_id] = "waiting_laundry_time"
    await message.answer(
        "Во сколько вы собираетесь стираться?\nНапишите время в формате 18:30",
        keyboard=empty_menu
    )


@bot.on.message(text="📨 Обратная связь")
async def feedback_start(message: Message):
    if not await require_private_message(message):
        return

    resident = await require_resident(message)
    if resident is None:
        return

    user_states[message.peer_id] = "waiting_feedback"
    await message.answer("Опишите ваше предложение одним сообщением:", keyboard=empty_menu)


@bot.on.message(text="🏪 Торговый зал")
async def market_start(message: Message):
    if not await require_private_message(message):
        return

    resident = await require_resident(message)
    if resident is None:
        return

    await message.answer(
        "Торговый зал: можно разместить объявление, посмотреть объявления или удалить своё.",
        keyboard=market_menu
    )


@bot.on.message(text="➕ Разместить объявление")
async def market_create_start(message: Message):
    if not await require_private_message(message):
        return

    resident = await require_resident(message)
    if resident is None:
        return

    user_states[message.peer_id] = "waiting_market_title"
    user_data.pop(message.peer_id, None)

    await message.answer(
        "Напиши название объявления.\nНапример: 'Продам холодильник' или 'Маникюр на заказ'.",
        keyboard=empty_menu
    )


@bot.on.message(text="📋 Смотреть объявления")
async def market_list_handler(message: Message):
    if not await require_private_message(message):
        return

    resident = await require_resident(message)
    if resident is None:
        return

    ads = get_market_ad_titles(50)

    if not ads:
        await message.answer("Сейчас в торговом зале нет объявлений.", keyboard=market_menu)
        return

    user_states[message.peer_id] = "waiting_market_view_choice"
    user_data[message.peer_id] = {"market_ads": ads}

    lines = []
    for index, ad in enumerate(ads, start=1):
        ad_id, title, creator_name, created_at = ad
        lines.append(f"{index}. {title}")

    await message.answer(
        "Объявления:\n\n"
        + "\n".join(lines)
        + "\n\nОтправь номер объявления, чтобы открыть карточку.",
        keyboard=empty_menu
    )


@bot.on.message(text="🗑 Удалить объявление")
async def market_delete_start(message: Message):
    if not await require_private_message(message):
        return

    resident = await require_resident(message)
    if resident is None:
        return

    is_manager = is_management(message.from_id, resident)
    ads = get_market_ads_for_delete(message.from_id, is_manager, 50)

    if not ads:
        await message.answer("У тебя нет доступных для удаления объявлений.", keyboard=market_menu)
        return

    user_states[message.peer_id] = "waiting_market_delete_choice"
    user_data[message.peer_id] = {
        "market_delete_ads": ads,
        "market_delete_is_manager": is_manager
    }

    lines = []
    for index, ad in enumerate(ads, start=1):
        ad_id, title, creator_name, created_at = ad
        if is_manager:
            lines.append(f"{index}. {title} — автор: {creator_name}")
        else:
            lines.append(f"{index}. {title}")

    await message.answer(
        "Выбери объявление для удаления:\n\n"
        + "\n".join(lines)
        + "\n\nОтправь номер объявления.",
        keyboard=empty_menu
    )


@bot.on.message(text="💬 Чаты")
async def chat_add(message: Message):
    if not await require_private_message(message):
        return

    resident = await require_resident(message)
    if resident is None:
        return

    if not can_see_chats(resident):
        await show_main_menu(message)
        return

    await message.answer("Выбери чат:", keyboard=build_chats_menu(resident))


@bot.on.message(text="👑 Администрирование")
async def management_handler(message: Message):
    if not await require_private_message(message):
        return

    resident = await require_management(message)
    if resident is None:
        return

    await message.answer("Раздел администрации:", keyboard=admin_menu)


@bot.on.message(text="Просмотр жалоб")
async def complaints_list_handler(message: Message):
    if not await require_private_message(message):
        return

    resident = await require_management(message)
    if resident is None:
        return

    complaints = get_issues_by_type("complaint", 15)

    if not complaints:
        await message.answer("Сейчас жалоб нет.", keyboard=admin_menu)
        return

    lines = []
    for item in complaints:
        issue_id, creator_vk_id, creator_name, room_number, user_block, issue_type, issue_text, status, created_at = item
        lines.append(
            f"Жалоба #{issue_id}\n"
            f"От: {creator_name}\n"
            f"Комната: {room_number}\n"
            f"Блок: {user_block}\n"
            f"Текст: {issue_text[:250]}\n"
            f"Дата: {created_at}"
        )

    await message.answer("Последние жалобы:\n\n" + "\n\n".join(lines), keyboard=admin_menu)


@bot.on.message(text="Просмотр заявок")
async def requests_list_handler(message: Message):
    if not await require_private_message(message):
        return

    resident = await require_management(message)
    if resident is None:
        return

    requests_list = get_issues_by_type("request", 15)

    if not requests_list:
        await message.answer("Сейчас заявок нет.", keyboard=admin_menu)
        return

    lines = []
    for item in requests_list:
        issue_id, creator_vk_id, creator_name, room_number, user_block, issue_type, issue_text, status, created_at = item
        lines.append(
            f"Заявка #{issue_id}\n"
            f"От: {creator_name}\n"
            f"Комната: {room_number}\n"
            f"Блок: {user_block}\n"
            f"Текст: {issue_text[:250]}\n"
            f"Дата: {created_at}"
        )

    await message.answer("Последние заявки:\n\n" + "\n\n".join(lines), keyboard=admin_menu)


@bot.on.message(text="Одобрение регистрации")
async def approval_requests_start(message: Message):
    if not await require_private_message(message):
        return

    resident = await require_management(message)
    if resident is None:
        return

    requests = [request_to_dict(row) for row in get_pending_requests()]

    if not requests:
        await message.answer("Сейчас нет заявок на регистрацию.", keyboard=admin_menu)
        return

    user_states[message.peer_id] = "waiting_approval_choice"
    user_data[message.peer_id] = {"pending_requests": requests}

    lines = []
    for index, request in enumerate(requests, start=1):
        lines.append(f"{index}. {request['full_name']} — {request['room_number']} — {request['study_group']}")

    await message.answer(
        "Заявки на регистрацию:\n\n"
        + "\n".join(lines)
        + "\n\nОтправь номер заявки.",
        keyboard=empty_menu
    )


@bot.on.message(text="🧺 Управление постирочной")
async def laundry_manage_start(message: Message):
    if not await require_private_message(message):
        return

    resident = await require_resident(message)
    if resident is None:
        return

    if not (is_laundry_direct_manager(message.from_id, resident) or is_laundry_pool_manager(message.from_id, resident)):
        await message.answer("У тебя нет доступа к управлению постирочной.")
        return

    keyboard = Keyboard(inline=False)

    if is_laundry_direct_manager(message.from_id, resident):
        keyboard.add(Text("Мои заявки постирочной"))

    if is_laundry_pool_manager(message.from_id, resident):
        if is_laundry_direct_manager(message.from_id, resident):
            keyboard.row()
        keyboard.add(Text("Общий пул постирочной"))

    keyboard.row()
    keyboard.add(Text("🔙 Назад"))

    await message.answer("Раздел постирочной:", keyboard=keyboard)


@bot.on.message(text="Мои заявки постирочной")
async def my_laundry_requests_handler(message: Message):
    if not await require_private_message(message):
        return

    resident = await require_resident(message)
    if resident is None:
        return

    if not is_laundry_direct_manager(message.from_id, resident):
        await message.answer("У тебя нет доступа к этим заявкам.")
        return

    requests = [
        laundry_request_to_dict(row)
        for row in get_pending_direct_laundry_requests(message.from_id)
    ]

    if not requests:
        await message.answer("У тебя нет новых заявок постирочной.")
        await show_main_menu(message)
        return

    user_states[message.peer_id] = "waiting_laundry_direct_choice"
    user_data[message.peer_id] = {"laundry_direct_requests": requests}

    lines = []
    for index, item in enumerate(requests, start=1):
        lines.append(
            f"{index}. {item['creator_name']} — комната {item['room_number']} — время {item['requested_time']}"
        )

    await message.answer(
        "Твои заявки постирочной:\n\n"
        + "\n".join(lines)
        + "\n\nОтправь номер заявки.",
        keyboard=empty_menu
    )


@bot.on.message(text="Общий пул постирочной")
async def pool_laundry_requests_handler(message: Message):
    if not await require_private_message(message):
        return

    resident = await require_resident(message)
    if resident is None:
        return

    if not is_laundry_pool_manager(message.from_id, resident):
        await message.answer("У тебя нет доступа к общему пулу.")
        return

    requests = [
        laundry_request_to_dict(row)
        for row in get_pending_pool_laundry_requests()
    ]

    if not requests:
        await message.answer("Общий пул постирочной сейчас пуст.")
        await show_main_menu(message)
        return

    user_states[message.peer_id] = "waiting_laundry_pool_choice"
    user_data[message.peer_id] = {"laundry_pool_requests": requests}

    lines = []
    for index, item in enumerate(requests, start=1):
        lines.append(
            f"{index}. {item['creator_name']} — комната {item['room_number']} — время {item['requested_time']}"
        )

    await message.answer(
        "Общий пул заявок постирочной:\n\n"
        + "\n".join(lines)
        + "\n\nОтправь номер заявки.",
        keyboard=empty_menu
    )


@bot.on.message()
async def catch_all(message: Message):
    if not await require_private_message(message):
        return

    state = user_states.get(message.peer_id)
    text = (message.text or "").strip()

    if state == "waiting_reg_full_name":
        if not FIO_PATTERN.fullmatch(text):
            await message.answer("Некорректное ФИО.\nВведите в формате: Иванов Иван Иванович")
            return

        user_data[message.peer_id] = {"full_name": text}
        user_states[message.peer_id] = "waiting_reg_room"
        await message.answer("В какой комнате проживаете?\nНапример: 123 или 123А")
        return

    if state == "waiting_reg_room":
        room_number = text.upper()
        match = ROOM_PATTERN.fullmatch(room_number)

        if not match:
            await message.answer("Некорректный номер комнаты.\nВведите число и при необходимости одну букву: 123 или 123А")
            return

        room_num = int(match.group(1))
        if not 1 <= room_num <= 150:
            await message.answer("Некорректный номер комнаты.\nВведите номер от 1 до 150: 123 или 123А")
            return

        user_data[message.peer_id]["room_number"] = room_number
        user_states[message.peer_id] = "waiting_reg_group"
        await message.answer("Напиши свою учебную группу.\nНапример: ИС-21 или П-103")
        return

    if state == "waiting_reg_group":
        study_group = text.upper()

        if len(study_group) < 2:
            await message.answer("Группа указана слишком коротко. Напиши нормально, например: ИС-21")
            return

        full_name = user_data[message.peer_id]["full_name"]
        room_number = user_data[message.peer_id]["room_number"]
        user_block = get_user_block(room_number)

        ok = verify_user(message.from_id, full_name, room_number, study_group, user_block)

        user_states.pop(message.peer_id, None)
        user_data.pop(message.peer_id, None)
        resident_cache.pop(message.from_id, None)

        if not ok:
            await message.answer("Не удалось отправить заявку. Попробуй ещё раз позже.")
            return

        await message.answer(
            "Заявка на регистрацию отправлена руководству.\n"
            "После подтверждения ты получишь доступ к боту."
        )
        return

    if state == "waiting_approval_choice":
        pending_requests = user_data.get(message.peer_id, {}).get("pending_requests", [])

        if not text.isdigit():
            await message.answer("Отправь номер заявки цифрой.")
            return

        index = int(text) - 1
        if index < 0 or index >= len(pending_requests):
            await message.answer("Заявки с таким номером нет.")
            return

        selected_request = pending_requests[index]
        user_data[message.peer_id]["selected_request"] = selected_request
        user_states[message.peer_id] = "waiting_approval_action"

        await message.answer(
            f"Заявка #{selected_request['id']}\n"
            f"ФИО: {selected_request['full_name']}\n"
            f"Комната: {selected_request['room_number']}\n"
            f"Группа: {selected_request['study_group']}\n"
            f"Блок: {selected_request['user_block']}\n\n"
            f"Нажми 'Одобрить' или 'Отклонить'.",
            keyboard=approval_action_menu
        )
        return

    if state == "waiting_approval_action":
        selected_request = user_data.get(message.peer_id, {}).get("selected_request")

        if selected_request is None:
            user_states.pop(message.peer_id, None)
            user_data.pop(message.peer_id, None)
            await show_main_menu(message)
            return

        if text == "Одобрить":
            approved_vk_id = approve_registration_request(selected_request["id"], message.from_id)

            user_states.pop(message.peer_id, None)
            user_data.pop(message.peer_id, None)

            if approved_vk_id is not None:
                resident_cache.pop(approved_vk_id, None)
                await safe_notify_user(
                    approved_vk_id,
                    "Твоя регистрация одобрена. Теперь можешь пользоваться ботом.\n"
                    "Напиши 'Начать' или 'меню', чтобы открыть главное меню."
                )

            await message.answer("Заявка одобрена.")
            await show_main_menu(message)
            return

        if text == "Отклонить":
            rejected_vk_id = reject_registration_request(selected_request["id"], message.from_id)

            user_states.pop(message.peer_id, None)
            user_data.pop(message.peer_id, None)

            if rejected_vk_id is not None:
                await safe_notify_user(
                    rejected_vk_id,
                    "Твоя заявка на регистрацию отклонена. Заполни её заново."
                )

            await message.answer("Заявка отклонена.")
            await show_main_menu(message)
            return

        await message.answer("Нажми 'Одобрить' или 'Отклонить'.", keyboard=approval_action_menu)
        return

    if state == "waiting_laundry_time":
        resident = await require_resident(message)
        if resident is None:
            user_states.pop(message.peer_id, None)
            return

        normalized_time = text.replace(".", ":")

        if not TIME_PATTERN.fullmatch(normalized_time):
            await message.answer("Некорректное время. Напиши в формате 18:30.")
            return

        responsible = get_laundry_responsible(resident["user_block"])
        responsible_vk_id = responsible[0] if responsible is not None else None

        laundry_request_id = create_laundry_request(
            creator_vk_id=message.from_id,
            creator_name=resident["full_name"],
            room_number=resident["room_number"],
            user_block=resident["user_block"],
            requested_time=normalized_time,
            assigned_to=responsible_vk_id,
        )

        user_states.pop(message.peer_id, None)

        if not laundry_request_id:
            await message.answer("Не удалось создать заявку на постирочную. Попробуй позже.")
            await show_main_menu(message)
            return

        if responsible_vk_id is not None:
            await message.answer(
                f"Заявка на постирочную #{laundry_request_id} создана.\n"
                f"Сначала её увидит ответственный по постирочной."
            )
            await safe_notify_user(
                responsible_vk_id,
                f"Новая заявка на постирочную #{laundry_request_id}.\n"
                f"От: {resident['full_name']}\n"
                f"Комната: {resident['room_number']}\n"
                f"VK: {build_vk_profile_link(message.from_id)}\n"
                f"Время: {normalized_time}"
            )
        else:
            await message.answer(
                f"Заявка на постирочную #{laundry_request_id} создана.\n"
                f"Ответственный по постирочной не назначен, поэтому заявка сразу попала в общий пул."
            )

        await show_main_menu(message)
        return

    if state == "waiting_laundry_direct_choice":
        requests = user_data.get(message.peer_id, {}).get("laundry_direct_requests", [])

        if not text.isdigit():
            await message.answer("Отправь номер заявки цифрой.")
            return

        index = int(text) - 1
        if index < 0 or index >= len(requests):
            await message.answer("Заявки с таким номером нет.")
            return

        selected_request = requests[index]
        user_data[message.peer_id]["selected_laundry_request"] = selected_request
        user_states[message.peer_id] = "waiting_laundry_direct_action"

        await message.answer(
            f"Заявка #{selected_request['id']}\n"
            f"От: {selected_request['creator_name']}\n"
            f"Комната: {selected_request['room_number']}\n"
            f"Блок: {selected_request['user_block']}\n"
            f"Время: {selected_request['requested_time']}\n\n"
            f"Нажми 'Принять' или 'В общий пул'.",
            keyboard=laundry_direct_action_menu
        )
        return

    if state == "waiting_laundry_direct_action":
        selected_request = user_data.get(message.peer_id, {}).get("selected_laundry_request")

        if selected_request is None:
            user_states.pop(message.peer_id, None)
            user_data.pop(message.peer_id, None)
            await show_main_menu(message)
            return

        if text == "Принять":
            ok = accept_laundry_request(selected_request["id"], message.from_id)

            user_states.pop(message.peer_id, None)
            user_data.pop(message.peer_id, None)

            if ok:
                await message.answer("Заявка на постирочную принята.")
                await notify_laundry_acceptance(message.from_id, selected_request)
            else:
                await message.answer("Не удалось принять заявку.")

            await show_main_menu(message)
            return

        if text == "В общий пул":
            ok = move_laundry_request_to_pool(selected_request["id"], message.from_id)

            user_states.pop(message.peer_id, None)
            user_data.pop(message.peer_id, None)

            if ok:
                await message.answer("Заявка отправлена в общий пул.")
            else:
                await message.answer("Не удалось перенести заявку в общий пул.")

            await show_main_menu(message)
            return

        await message.answer("Нажми 'Принять' или 'В общий пул'.", keyboard=laundry_direct_action_menu)
        return

    if state == "waiting_laundry_pool_choice":
        requests = user_data.get(message.peer_id, {}).get("laundry_pool_requests", [])

        if not text.isdigit():
            await message.answer("Отправь номер заявки цифрой.")
            return

        index = int(text) - 1
        if index < 0 or index >= len(requests):
            await message.answer("Заявки с таким номером нет.")
            return

        selected_request = requests[index]
        user_data[message.peer_id]["selected_laundry_pool_request"] = selected_request
        user_states[message.peer_id] = "waiting_laundry_pool_action"

        await message.answer(
            f"Заявка #{selected_request['id']}\n"
            f"От: {selected_request['creator_name']}\n"
            f"Комната: {selected_request['room_number']}\n"
            f"Блок: {selected_request['user_block']}\n"
            f"Время: {selected_request['requested_time']}\n\n"
            f"Нажми 'Принять'.",
            keyboard=laundry_pool_action_menu
        )
        return

    if state == "waiting_laundry_pool_action":
        selected_request = user_data.get(message.peer_id, {}).get("selected_laundry_pool_request")

        if selected_request is None:
            user_states.pop(message.peer_id, None)
            user_data.pop(message.peer_id, None)
            await show_main_menu(message)
            return

        if text == "Принять":
            ok = accept_laundry_request(selected_request["id"], message.from_id)

            user_states.pop(message.peer_id, None)
            user_data.pop(message.peer_id, None)

            if ok:
                await message.answer("Заявка из общего пула принята.")
                await notify_laundry_acceptance(message.from_id, selected_request)
            else:
                await message.answer("Не удалось принять заявку.")

            await show_main_menu(message)
            return

        await message.answer("Нажми 'Принять'.", keyboard=laundry_pool_action_menu)
        return

    if state == "waiting_request":
        resident = await require_resident(message)
        if resident is None:
            user_states.pop(message.peer_id, None)
            return

        if not text or len(text) < 5:
            await message.answer("Опиши проблему подробнее.")
            return

        user_states.pop(message.peer_id, None)
        await submit_issue(message, resident, "request", text)
        return

    if state == "waiting_complaint":
        resident = await require_resident(message)
        if resident is None:
            user_states.pop(message.peer_id, None)
            return

        if not text or len(text) < 5:
            await message.answer("Опиши жалобу подробнее.")
            return

        user_states.pop(message.peer_id, None)
        await submit_issue(message, resident, "complaint", text)
        return

    if state == "waiting_feedback":
        resident = await require_resident(message)
        if resident is None:
            user_states.pop(message.peer_id, None)
            return

        if not text or len(text) < 5:
            await message.answer("Слишком коротко. Опишите подробнее.")
            return

        feedback_id = create_feedback_message(
            creator_vk_id=message.from_id,
            creator_name=resident["full_name"],
            room_number=resident["room_number"],
            user_block=resident["user_block"],
            text=text,
        )

        user_states.pop(message.peer_id, None)

        if not feedback_id:
            await message.answer("Не удалось сохранить обратную связь. Попробуй позже.")
            await show_main_menu(message)
            return

        await message.answer(f"Сообщение обратной связи сохранено под номером #{feedback_id}. Спасибо.")
        await show_main_menu(message)
        return

    if state == "waiting_market_title":
        resident = await require_resident(message)
        if resident is None:
            user_states.pop(message.peer_id, None)
            user_data.pop(message.peer_id, None)
            return

        if len(text) < 3:
            await message.answer("Название слишком короткое. Напиши минимум 3 символа.")
            return

        user_data[message.peer_id] = {"market_title": text}
        user_states[message.peer_id] = "waiting_market_description"

        await message.answer(
            "Теперь опиши объявление подробно.\n"
            "Например: состояние товара, цена, условия, когда можно забрать.",
            keyboard=empty_menu
        )
        return

    if state == "waiting_market_description":
        resident = await require_resident(message)
        if resident is None:
            user_states.pop(message.peer_id, None)
            user_data.pop(message.peer_id, None)
            return

        if len(text) < 10:
            await message.answer("Описание слишком короткое. Напиши подробнее.")
            return

        user_data[message.peer_id]["market_description"] = text
        user_states[message.peer_id] = "waiting_market_contacts"

        await message.answer(
            "Оставь контакты для связи.\n"
            "Например: телефон, VK, Telegram или 'пиши в личку'.",
            keyboard=empty_menu
        )
        return

    if state == "waiting_market_contacts":
        resident = await require_resident(message)
        if resident is None:
            user_states.pop(message.peer_id, None)
            user_data.pop(message.peer_id, None)
            return

        if len(text) < 5:
            await message.answer("Контакты слишком короткие. Напиши понятнее.")
            return

        market_title = user_data.get(message.peer_id, {}).get("market_title")
        market_description = user_data.get(message.peer_id, {}).get("market_description")

        ad_id = create_market_ad(
            creator_vk_id=message.from_id,
            creator_name=resident["full_name"],
            room_number=resident["room_number"],
            user_block=resident["user_block"],
            title=market_title,
            description=market_description,
            contacts=text,
        )

        user_states.pop(message.peer_id, None)
        user_data.pop(message.peer_id, None)

        if not ad_id:
            await message.answer("Не удалось сохранить объявление. Попробуй позже.")
            await show_main_menu(message)
            return

        await message.answer(f"Объявление #{ad_id} опубликовано в торговом зале.", keyboard=market_menu)
        return

    if state == "waiting_market_view_choice":
        ads = user_data.get(message.peer_id, {}).get("market_ads", [])

        if not text.isdigit():
            await message.answer("Отправь номер объявления цифрой.")
            return

        index = int(text) - 1
        if index < 0 or index >= len(ads):
            await message.answer("Объявления с таким номером нет.")
            return

        ad_id = ads[index][0]
        ad = market_ad_to_dict(get_market_ad(ad_id))

        if ad is None:
            await message.answer("Не удалось открыть карточку объявления.")
            return

        user_states.pop(message.peer_id, None)
        user_data.pop(message.peer_id, None)

        await message.answer(
            f"Объявление #{ad['id']}\n"
            f"Название: {ad['title']}\n"
            f"Автор: {ad['creator_name']}\n"
            f"Комната: {ad['room_number']}\n"
            f"Блок: {ad['user_block']}\n"
            f"Описание: {ad['description']}\n"
            f"Контакты: {ad['contacts']}"
        )
        await message.answer("Можешь посмотреть другие объявления:", keyboard=market_menu)
        return

    if state == "waiting_market_delete_choice":
        ads = user_data.get(message.peer_id, {}).get("market_delete_ads", [])

        if not text.isdigit():
            await message.answer("Отправь номер объявления цифрой.")
            return

        index = int(text) - 1
        if index < 0 or index >= len(ads):
            await message.answer("Объявления с таким номером нет.")
            return

        selected_ad = ads[index]
        user_data[message.peer_id]["selected_delete_ad"] = selected_ad
        user_states[message.peer_id] = "waiting_market_delete_confirm"

        await message.answer(
            f"Удалить объявление:\n{selected_ad[1]} ?",
            keyboard=delete_ad_confirm_menu
        )
        return

    if state == "waiting_market_delete_confirm":
        selected_ad = user_data.get(message.peer_id, {}).get("selected_delete_ad")
        is_manager = user_data.get(message.peer_id, {}).get("market_delete_is_manager", False)

        if selected_ad is None:
            user_states.pop(message.peer_id, None)
            user_data.pop(message.peer_id, None)
            await show_main_menu(message)
            return

        if text == "Отмена":
            user_states.pop(message.peer_id, None)
            user_data.pop(message.peer_id, None)
            await message.answer("Удаление отменено.", keyboard=market_menu)
            return

        if text == "Удалить":
            ok = delete_market_ad(selected_ad[0], message.from_id, is_manager)

            user_states.pop(message.peer_id, None)
            user_data.pop(message.peer_id, None)

            if ok:
                await message.answer("Объявление удалено.", keyboard=market_menu)
            else:
                await message.answer("Не удалось удалить объявление.", keyboard=market_menu)
            return

        await message.answer("Нажми 'Удалить' или 'Отмена'.", keyboard=delete_ad_confirm_menu)
        return

    resident = get_current_resident(message.from_id)
    if resident is None:
        request = get_current_request(message.from_id)

        if request is not None and request["status"] == "pending":
            return

        restored = await restore_menu_if_needed(message)
        if restored:
            return

        await start_registration(message)
        return

    restored = await restore_menu_if_needed(message)
    if restored:
        return

    await show_main_menu(message)


if __name__ == "__main__":
    bot.run_forever()
