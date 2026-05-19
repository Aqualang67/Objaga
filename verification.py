import re
from Database import create_registration_request


def verify_user(vk_id: int, full_name: str, room_number: str, study_group: str, user_block: str = ""):
    full_name = (full_name or "").strip().upper()
    room_number = (room_number or "").strip().upper()
    study_group = (study_group or "").strip().upper()

    if not user_block:
        user_block = get_user_block(room_number)

    return create_registration_request(vk_id, full_name, room_number, study_group, user_block)


def get_user_block(room_number: str):
    room_number = (room_number or "").strip().upper()

    match = re.fullmatch(r"(\d+)[А-ЯЁ]?", room_number)
    if not match:
        return ""

    room_num = int(match.group(1))

    if room_num < 17:
        return "1 этаж"
    elif room_num in range(17, 29) or room_num in range(45, 49):
        return "2 левый"
    elif room_num in range(29, 45):
        return "2 правый"
    elif room_num in range(49, 61) or room_num in range(77, 81):
        return "3 левый"
    elif room_num in range(61, 77):
        return "3 правый"
    elif room_num in range(81, 93) or room_num in range(109, 113):
        return "4 левый"
    elif room_num in range(93, 109):
        return "4 правый"
    elif room_num in range(113, 125) or room_num in range(141, 145):
        return "5 левый"
    elif room_num in range(125, 141):
        return "5 правый"
    else:
        return "Неизвестный блок"