import os
import sqlite3
from datetime import datetime


SHARED_DIR = os.getenv("SHARED_DIR", "/app/shared")
os.makedirs(SHARED_DIR, exist_ok=True)
DB_FILE = os.path.join(SHARED_DIR, "dormitory.db")


def normalize_roles(job_value: str) -> str:
    items = []

    for part in (job_value or "").split(","):
        role = part.strip()
        if role and role not in items:
            items.append(role)

    return ",".join(items) if items else "Проживающий"


def parse_roles(job_value: str):
    return [item.strip() for item in normalize_roles(job_value).split(",") if item.strip()]


def has_any_role(job_value: str, *roles):
    current_roles = set(parse_roles(job_value))
    return any(role in current_roles for role in roles)


def ensure_column(conn, table_name: str, column_name: str, column_sql: str):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]

    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


def init_db():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS residents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vk_id INTEGER UNIQUE,
                full_name TEXT NOT NULL,
                room_number TEXT,
                study_group TEXT DEFAULT '',
                user_block TEXT,
                phone TEXT,
                created_at TEXT,
                job TEXT
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS registration_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vk_id INTEGER UNIQUE,
                full_name TEXT NOT NULL,
                room_number TEXT NOT NULL,
                study_group TEXT DEFAULT '',
                user_block TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT,
                updated_at TEXT,
                reviewed_by INTEGER,
                reviewed_at TEXT
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_vk_id INTEGER NOT NULL,
                creator_name TEXT NOT NULL,
                room_number TEXT NOT NULL,
                user_block TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_vk_id INTEGER NOT NULL,
                creator_name TEXT NOT NULL,
                room_number TEXT NOT NULL,
                user_block TEXT NOT NULL,
                issue_type TEXT NOT NULL,
                issue_text TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new',
                created_at TEXT NOT NULL
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS laundry_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_vk_id INTEGER NOT NULL,
                creator_name TEXT NOT NULL,
                room_number TEXT NOT NULL,
                user_block TEXT NOT NULL,
                requested_time TEXT NOT NULL,
                status TEXT NOT NULL,
                assigned_to INTEGER,
                reviewed_by INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_ads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_vk_id INTEGER NOT NULL,
                creator_name TEXT NOT NULL,
                room_number TEXT NOT NULL,
                user_block TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                contacts TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """)

            ensure_column(conn, "residents", "study_group", "study_group TEXT DEFAULT ''")
            ensure_column(conn, "registration_requests", "study_group", "study_group TEXT DEFAULT ''")

        return True
    except sqlite3.Error as e:
        print(f"Ошибка init_db: {e}")
        return False


def add_resident(
    vk_id: int,
    full_name: str,
    room_number: str,
    user_block: str,
    study_group: str = "",
    phone: str = "",
    job: str = "Проживающий",
):
    try:
        normalized_job = normalize_roles(job)

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO residents (
                vk_id, full_name, room_number, study_group, user_block, phone, job, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(vk_id) DO UPDATE SET
                full_name = excluded.full_name,
                room_number = excluded.room_number,
                study_group = excluded.study_group,
                user_block = excluded.user_block,
                phone = excluded.phone,
                job = excluded.job
            """, (
                vk_id,
                full_name,
                room_number,
                study_group,
                user_block,
                phone,
                normalized_job,
                datetime.now().isoformat()
            ))
        return True
    except sqlite3.Error as e:
        print(f"Ошибка add_resident: {e}")
        return False


def get_resident(vk_id: int):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT full_name, room_number, study_group, phone, user_block, job
            FROM residents
            WHERE vk_id = ?
            """, (vk_id,))
            return cursor.fetchone()
    except sqlite3.Error as e:
        print(f"Ошибка get_resident: {e}")
        return None


def get_all_residents():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT vk_id, full_name, room_number, study_group, user_block, job
            FROM residents
            """)
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Ошибка get_all_residents: {e}")
        return []


def update_resident(
    vk_id: int,
    full_name: str = None,
    room_number: str = None,
    study_group: str = None,
    user_block: str = None,
    phone: str = None,
):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()

            if full_name is not None:
                cursor.execute(
                    "UPDATE residents SET full_name = ? WHERE vk_id = ?",
                    (full_name, vk_id)
                )

            if room_number is not None:
                cursor.execute(
                    "UPDATE residents SET room_number = ?, user_block = ? WHERE vk_id = ?",
                    (room_number, user_block, vk_id)
                )

            if study_group is not None:
                cursor.execute(
                    "UPDATE residents SET study_group = ? WHERE vk_id = ?",
                    (study_group, vk_id)
                )

            if phone is not None:
                cursor.execute(
                    "UPDATE residents SET phone = ? WHERE vk_id = ?",
                    (phone, vk_id)
                )

        return True
    except sqlite3.Error as e:
        print(f"Ошибка update_resident: {e}")
        return False


def hire_resident(vk_id: int, job: str):
    try:
        normalized_job = normalize_roles(job)

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE residents SET job = ? WHERE vk_id = ?",
                (normalized_job, vk_id)
            )
        return True
    except sqlite3.Error as e:
        print(f"Ошибка hire_resident: {e}")
        return False


def add_resident_role(vk_id: int, role: str):
    try:
        role = (role or "").strip()
        if not role:
            return False

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT job FROM residents WHERE vk_id = ?", (vk_id,))
            row = cursor.fetchone()

            if row is None:
                return False

            roles = parse_roles(row[0] or "")
            if role not in roles:
                roles.append(role)

            cursor.execute(
                "UPDATE residents SET job = ? WHERE vk_id = ?",
                (normalize_roles(",".join(roles)), vk_id)
            )
        return True
    except sqlite3.Error as e:
        print(f"Ошибка add_resident_role: {e}")
        return False


def remove_resident_role(vk_id: int, role: str):
    try:
        role = (role or "").strip()
        if not role:
            return False

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT job FROM residents WHERE vk_id = ?", (vk_id,))
            row = cursor.fetchone()

            if row is None:
                return False

            roles = [item for item in parse_roles(row[0] or "") if item != role]

            cursor.execute(
                "UPDATE residents SET job = ? WHERE vk_id = ?",
                (normalize_roles(",".join(roles)), vk_id)
            )
        return True
    except sqlite3.Error as e:
        print(f"Ошибка remove_resident_role: {e}")
        return False


def create_registration_request(
    vk_id: int,
    full_name: str,
    room_number: str,
    study_group: str,
    user_block: str,
):
    try:
        now = datetime.now().isoformat()

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO registration_requests (
                vk_id, full_name, room_number, study_group, user_block,
                status, created_at, updated_at, reviewed_by, reviewed_at
            )
            VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, NULL, NULL)
            ON CONFLICT(vk_id) DO UPDATE SET
                full_name = excluded.full_name,
                room_number = excluded.room_number,
                study_group = excluded.study_group,
                user_block = excluded.user_block,
                status = 'pending',
                created_at = excluded.created_at,
                updated_at = excluded.updated_at,
                reviewed_by = NULL,
                reviewed_at = NULL
            """, (vk_id, full_name, room_number, study_group, user_block, now, now))
        return True
    except sqlite3.Error as e:
        print(f"Ошибка create_registration_request: {e}")
        return False


def get_registration_request(vk_id: int):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT id, vk_id, full_name, room_number, study_group, user_block, status, created_at
            FROM registration_requests
            WHERE vk_id = ?
            """, (vk_id,))
            return cursor.fetchone()
    except sqlite3.Error as e:
        print(f"Ошибка get_registration_request: {e}")
        return None


def get_pending_requests():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT id, vk_id, full_name, room_number, study_group, user_block, status, created_at
            FROM registration_requests
            WHERE status = 'pending'
            ORDER BY created_at
            """)
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Ошибка get_pending_requests: {e}")
        return []


def approve_registration_request(request_id: int, reviewed_by: int):
    try:
        now = datetime.now().isoformat()

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()

            cursor.execute("""
            SELECT vk_id, full_name, room_number, study_group, user_block
            FROM registration_requests
            WHERE id = ? AND status = 'pending'
            """, (request_id,))
            row = cursor.fetchone()

            if row is None:
                return None

            vk_id, full_name, room_number, study_group, user_block = row

            cursor.execute("""
            INSERT INTO residents (
                vk_id, full_name, room_number, study_group, user_block, phone, job, created_at
            )
            VALUES (?, ?, ?, ?, ?, '', 'Проживающий', ?)
            ON CONFLICT(vk_id) DO UPDATE SET
                full_name = excluded.full_name,
                room_number = excluded.room_number,
                study_group = excluded.study_group,
                user_block = excluded.user_block
            """, (vk_id, full_name, room_number, study_group, user_block, now))

            cursor.execute("""
            UPDATE registration_requests
            SET status = 'approved',
                updated_at = ?,
                reviewed_by = ?,
                reviewed_at = ?
            WHERE id = ?
            """, (now, reviewed_by, now, request_id))

            return vk_id
    except sqlite3.Error as e:
        print(f"Ошибка approve_registration_request: {e}")
        return None


def reject_registration_request(request_id: int, reviewed_by: int):
    try:
        now = datetime.now().isoformat()

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()

            cursor.execute("""
            SELECT vk_id
            FROM registration_requests
            WHERE id = ? AND status = 'pending'
            """, (request_id,))
            row = cursor.fetchone()

            if row is None:
                return None

            vk_id = row[0]

            cursor.execute("""
            UPDATE registration_requests
            SET status = 'rejected',
                updated_at = ?,
                reviewed_by = ?,
                reviewed_at = ?
            WHERE id = ?
            """, (now, reviewed_by, now, request_id))

            return vk_id
    except sqlite3.Error as e:
        print(f"Ошибка reject_registration_request: {e}")
        return None


def create_issue(
    creator_vk_id: int,
    creator_name: str,
    room_number: str,
    user_block: str,
    issue_type: str,
    issue_text: str,
):
    try:
        now = datetime.now().isoformat()

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO issues (
                creator_vk_id, creator_name, room_number, user_block,
                issue_type, issue_text, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'new', ?)
            """, (
                creator_vk_id,
                creator_name,
                room_number,
                user_block,
                issue_type,
                issue_text,
                now
            ))
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Ошибка create_issue: {e}")
        return None


def count_user_issues_today(creator_vk_id: int):
    try:
        start_of_day = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT COUNT(*)
            FROM issues
            WHERE creator_vk_id = ?
            AND created_at >= ?
            """, (creator_vk_id, start_of_day))
            row = cursor.fetchone()
            return row[0] if row else 0
    except sqlite3.Error as e:
        print(f"Ошибка count_user_issues_today: {e}")
        return 0


def get_issue_recipients(user_block: str):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT vk_id, full_name, job, user_block
            FROM residents
            """)
            rows = cursor.fetchall()

        result = []
        for vk_id, full_name, job, resident_block in rows:
            if resident_block == user_block and has_any_role(job, "Староста", "Ответственный"):
                result.append((vk_id, full_name, job, resident_block))
                continue

            if has_any_role(job, "Председатель", "Администрация"):
                result.append((vk_id, full_name, job, resident_block))

        return result
    except sqlite3.Error as e:
        print(f"Ошибка get_issue_recipients: {e}")
        return []


def create_feedback_message(
    creator_vk_id: int,
    creator_name: str,
    room_number: str,
    user_block: str,
    text: str,
):
    try:
        now = datetime.now().isoformat()

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO feedback_messages (
                creator_vk_id, creator_name, room_number, user_block, text, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                creator_vk_id,
                creator_name,
                room_number,
                user_block,
                text,
                now
            ))
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Ошибка create_feedback_message: {e}")
        return None


def get_feedback_messages(limit: int = 20):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT id, creator_name, room_number, user_block, text, created_at
            FROM feedback_messages
            ORDER BY created_at DESC
            LIMIT ?
            """, (limit,))
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Ошибка get_feedback_messages: {e}")
        return []


def get_laundry_responsible(user_block: str = None):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT vk_id, full_name, job, user_block
            FROM residents
            ORDER BY id
            """)
            rows = cursor.fetchall()

        for vk_id, full_name, job, resident_block in rows:
            if user_block is not None and resident_block != user_block:
                continue

            if has_any_role(job, "Ответственный по постирочной"):
                return vk_id, full_name

        return None
    except sqlite3.Error as e:
        print(f"Ошибка get_laundry_responsible: {e}")
        return None


def create_laundry_request(
    creator_vk_id: int,
    creator_name: str,
    room_number: str,
    user_block: str,
    requested_time: str,
    assigned_to=None,
):
    try:
        now = datetime.now().isoformat()
        status = "pending_direct" if assigned_to is not None else "pending_pool"

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO laundry_requests (
                creator_vk_id, creator_name, room_number, user_block,
                requested_time, status, assigned_to, reviewed_by, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
            """, (
                creator_vk_id,
                creator_name,
                room_number,
                user_block,
                requested_time,
                status,
                assigned_to,
                now,
                now
            ))
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Ошибка create_laundry_request: {e}")
        return None


def get_pending_direct_laundry_requests(responsible_vk_id: int):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT id, creator_vk_id, creator_name, room_number, user_block,
                   requested_time, status, assigned_to, created_at
            FROM laundry_requests
            WHERE status = 'pending_direct' AND assigned_to = ?
            ORDER BY created_at
            """, (responsible_vk_id,))
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Ошибка get_pending_direct_laundry_requests: {e}")
        return []


def get_pending_pool_laundry_requests():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT id, creator_vk_id, creator_name, room_number, user_block,
                   requested_time, status, assigned_to, created_at
            FROM laundry_requests
            WHERE status = 'pending_pool'
            ORDER BY created_at
            """)
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Ошибка get_pending_pool_laundry_requests: {e}")
        return []


def move_laundry_request_to_pool(request_id: int, reviewed_by: int):
    try:
        now = datetime.now().isoformat()

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE laundry_requests
            SET status = 'pending_pool',
                assigned_to = NULL,
                reviewed_by = ?,
                updated_at = ?
            WHERE id = ? AND status = 'pending_direct'
            """, (reviewed_by, now, request_id))
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Ошибка move_laundry_request_to_pool: {e}")
        return False


def accept_laundry_request(request_id: int, reviewed_by: int):
    try:
        now = datetime.now().isoformat()

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE laundry_requests
            SET status = 'approved',
                assigned_to = ?,
                reviewed_by = ?,
                updated_at = ?
            WHERE id = ? AND status IN ('pending_direct', 'pending_pool')
            """, (reviewed_by, reviewed_by, now, request_id))
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Ошибка accept_laundry_request: {e}")
        return False


def create_market_ad(
    creator_vk_id: int,
    creator_name: str,
    room_number: str,
    user_block: str,
    title: str,
    description: str,
    contacts: str,
):
    try:
        now = datetime.now().isoformat()

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO market_ads (
                creator_vk_id, creator_name, room_number, user_block,
                title, description, contacts, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
            """, (
                creator_vk_id,
                creator_name,
                room_number,
                user_block,
                title,
                description,
                contacts,
                now,
                now
            ))
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Ошибка create_market_ad: {e}")
        return None


def get_market_ad_titles(limit: int = 50):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT id, title, creator_name, created_at
            FROM market_ads
            WHERE status = 'active'
            ORDER BY created_at DESC
            LIMIT ?
            """, (limit,))
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Ошибка get_market_ad_titles: {e}")
        return []


def get_market_ad(ad_id: int):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT id, creator_vk_id, creator_name, room_number, user_block,
                   title, description, contacts, status, created_at
            FROM market_ads
            WHERE id = ? AND status = 'active'
            """, (ad_id,))
            return cursor.fetchone()
    except sqlite3.Error as e:
        print(f"Ошибка get_market_ad: {e}")
        return None


def get_market_ads_for_delete(requester_vk_id: int, requester_is_management: bool, limit: int = 50):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()

            if requester_is_management:
                cursor.execute("""
                SELECT id, title, creator_name, created_at
                FROM market_ads
                WHERE status = 'active'
                ORDER BY created_at DESC
                LIMIT ?
                """, (limit,))
            else:
                cursor.execute("""
                SELECT id, title, creator_name, created_at
                FROM market_ads
                WHERE status = 'active' AND creator_vk_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """, (requester_vk_id, limit))

            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Ошибка get_market_ads_for_delete: {e}")
        return []


def delete_market_ad(ad_id: int, requester_vk_id: int, requester_is_management: bool = False):
    try:
        now = datetime.now().isoformat()

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT creator_vk_id
            FROM market_ads
            WHERE id = ? AND status = 'active'
            """, (ad_id,))
            row = cursor.fetchone()

            if row is None:
                return False

            creator_vk_id = row[0]

            if not requester_is_management and creator_vk_id != requester_vk_id:
                return False

            cursor.execute("""
            UPDATE market_ads
            SET status = 'deleted',
                updated_at = ?
            WHERE id = ?
            """, (now, ad_id))
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Ошибка delete_market_ad: {e}")
        return False


def get_issues_by_type(issue_type: str, limit: int = 20):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT id, creator_vk_id, creator_name, room_number, user_block,
                   issue_type, issue_text, status, created_at
            FROM issues
            WHERE issue_type = ?
            ORDER BY created_at DESC
            LIMIT ?
            """, (issue_type, limit))
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Ошибка get_issues_by_type: {e}")
        return []


if __name__ == "__main__":
    if init_db():
        print("База готова")
        print(f"Путь к базе: {DB_FILE}")
    else:
        print("Не удалось инициализировать базу")
