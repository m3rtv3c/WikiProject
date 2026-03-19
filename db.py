import psycopg2
from datetime import datetime
import re

DB_CONFIG = {
    "dbname": "wiki",
    "user": "postgres",
    "password": "123",
    "host": "localhost",
    "port": "5432"
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


# ================= USERS =================

def get_user_with_roles(login, password):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            u.id,
            u.name,
            u.login,
            u.email,
            r.name
        FROM users u
        LEFT JOIN user_role ur ON ur.id_user = u.id
        LEFT JOIN role r ON r.id = ur.id_role
        WHERE u.login=%s AND u.password=%s
    """, (login, password))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    user = {
        "id": rows[0][0],
        "name": rows[0][1],
        "login": rows[0][2],
        "email": rows[0][3],
        "roles": []
    }

    # собираем роли
    user["roles"] = list({row[4] for row in rows if row[4]})

    return user


def create_user(login, password, name, email):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO users(login,password,name,email,reg_date)
        VALUES(%s,%s,%s,%s,%s)
        RETURNING id
    """, (login, password, name, email, datetime.now()))

    user_id = cursor.fetchone()[0]

    # роль USER по умолчанию (id = 3)
    cursor.execute("""
        INSERT INTO user_role(id_user,id_role)
        VALUES(%s,3)
    """, (user_id,))

    conn.commit()
    conn.close()


# ================= ARTICLES =================

def get_articles(search=""):
    conn = get_connection()
    cursor = conn.cursor()

    if search:
        cursor.execute("""
            SELECT id,title,views
            FROM article
            WHERE status='published'
            AND title ILIKE %s
            ORDER BY views DESC
        """, (f"%{search}%",))
    else:
        cursor.execute("""
            SELECT id,title,views
            FROM article
            WHERE status='published'
            ORDER BY views DESC
        """)

    data = cursor.fetchall()
    conn.close()
    return data


def get_article_by_id(article_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id,title,content,views
        FROM article
        WHERE id=%s AND status='published'
    """, (article_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "title": row[1],
        "content": row[2],
        "views": row[3]
    }
def get_all_article_titles():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT title FROM article WHERE status='published'")
    titles = [row[0] for row in cur.fetchall()]

    conn.close()
    return titles

def auto_link_articles(text, titles):
    for title in sorted(titles, key=len, reverse=True):
        pattern = r'\b' + re.escape(title) + r'\b'

        text = re.sub(
            pattern,
            f'<a href="article:{title}">{title}</a>',
            text
        )

    return text


def get_all_articles(search=""):
    """
    Возвращает все статьи, независимо от статуса.
    Для админки.
    """
    conn = get_connection()
    cursor = conn.cursor()

    if search:
        cursor.execute("""
            SELECT id, title, views, status
            FROM article
            WHERE title ILIKE %s
            ORDER BY id DESC
        """, (f"%{search}%",))
    else:
        cursor.execute("""
            SELECT id, title, views, status
            FROM article
            ORDER BY id DESC
        """)

    data = cursor.fetchall()
    conn.close()
    return data

def increase_views(article_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE article
        SET views = views + 1
        WHERE id = %s
    """, (article_id,))

    conn.commit()
    conn.close()

# ================= ARTICLE IMAGES =================

def get_article_images(article_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT i.description
        FROM article_image ai
        JOIN image i ON ai.id_image = i.id
        WHERE ai.id_article = %s
        ORDER BY ai.id
    """, (article_id,))

    rows = cursor.fetchall()
    conn.close()

    return [row[0] for row in rows if row[0]]

def get_article_by_title(title):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id,title,content,views
        FROM article
        WHERE title=%s AND status='published'
    """, (title,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "title": row[1],
        "content": row[2],
        "views": row[3]
    }
def get_users():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM users")
    data = cur.fetchall()

    cur.close()
    conn.close()
    return data


def get_user_roles(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT r.name
        FROM role r
        JOIN user_role ur ON ur.id_role = r.id
        WHERE ur.id_user = %s
    """, (user_id,))

    roles = [r[0] for r in cur.fetchall()]

    cur.close()
    conn.close()
    return roles


def set_user_role(user_id, role_name):
    conn = get_connection()
    cur = conn.cursor()

    # получаем id роли
    cur.execute("SELECT id FROM role WHERE name = %s", (role_name,))
    role_id = cur.fetchone()[0]

    # очищаем роли
    cur.execute("DELETE FROM user_role WHERE id_user = %s", (user_id,))

    # добавляем новую
    cur.execute("""
        INSERT INTO user_role (id_user, id_role)
        VALUES (%s, %s)
    """, (user_id, role_id))

    conn.commit()
    cur.close()
    conn.close()


def get_full_history(article_id=None):
    conn = get_connection()
    cur = conn.cursor()

    if article_id:
        cur.execute("""
            SELECT 
                h.id,
                h.title,
                h.updated_at,
                h.status,
                h.views,
                u.name,
                h.id_article
            FROM article_history h
            LEFT JOIN users u ON u.id = h.id_user
            WHERE h.id_article = %s
            ORDER BY h.updated_at DESC
        """, (article_id,))
    else:
        cur.execute("""
            SELECT 
                h.id,
                h.title,
                h.updated_at,
                h.status,
                h.views,
                u.name,
                h.id_article
            FROM article_history h
            LEFT JOIN users u ON u.id = h.id_user
            ORDER BY h.updated_at DESC
            LIMIT 200
        """)

    data = cur.fetchall()

    cur.close()
    conn.close()
    return data

def get_history_by_id(history_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT title, content, id_article
        FROM article_history
        WHERE id = %s
    """, (history_id,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "title": row[0],
        "content": row[1],
        "id": history_id,
        "article_id": row[2]
    }

def rollback_article(history_id, user_id):
    conn = get_connection()
    cur = conn.cursor()

    # 1. получить версию
    cur.execute("""
        SELECT article_id, title, content
        FROM article_history
        WHERE id = %s
    """, (history_id,))
    article_id, title, content = cur.fetchone()

    # 2. обновить статью
    cur.execute("""
        UPDATE article
        SET title = %s,
            content = %s
        WHERE id = %s
    """, (title, content, article_id))

    # 3. заменить картинки
    cur.execute("DELETE FROM article_image WHERE id_article = %s", (article_id,))

    cur.execute("""
        SELECT id_image FROM article_image
        WHERE id_history = %s
    """, (history_id,))

    for (img_id,) in cur.fetchall():
        cur.execute("""
            INSERT INTO article_image (id_article, id_image)
            VALUES (%s, %s)
        """, (article_id, img_id))

    conn.commit()
    conn.close()

def soft_delete_article(article_id, user_id):
    conn = get_connection()
    cur = conn.cursor()

    # Сохраняем текущую версию в истории с статусом "deleted"
    cur.execute("""
        INSERT INTO article_history
        (title, content, updated_at, status, views, id_article, id_user)
        SELECT title, content, NOW(), 'deleted', views, id, %s
        FROM article
        WHERE id = %s
    """, (user_id, article_id))

    # Меняем статус статьи
    cur.execute("""
        UPDATE article
        SET status = 'deleted'
        WHERE id = %s
    """, (article_id,))

    conn.commit()
    cur.close()
    conn.close()

def update_article_status(article_id, status):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE article
        SET status = %s
        WHERE id = %s
    """, (status, article_id))

    conn.commit()
    conn.close()

def get_pending_articles():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, views, status
        FROM article
        WHERE status = 'pending'
        ORDER BY id DESC
    """)

    data = cur.fetchall()
    conn.close()
    return data

def approve_article_version(history_id, user_id):
    conn = get_connection()
    cur = conn.cursor()

    # 1. берём версию
    cur.execute("""
        SELECT id_article, title, content
        FROM article_history
        WHERE id = %s
    """, (history_id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        return

    article_id, title, content = row

    # 2. обновляем ОСНОВНУЮ статью
    cur.execute("""
        UPDATE article
        SET title = %s,
            content = %s,
            status = 'published'
        WHERE id = %s
    """, (title, content, article_id))

    # 3. помечаем версию как применённую
    cur.execute("""
        UPDATE article_history
        SET status = 'approved'
        WHERE id = %s
    """, (history_id,))

    conn.commit()
    conn.close()

def approve_new_article(article_id, user_id):
    conn = get_connection()
    cur = conn.cursor()

    # Ставим статус published
    cur.execute("""
        UPDATE article
        SET status = 'published'
        WHERE id = %s
    """, (article_id,))

    # Создаём запись в истории сразу как опубликованную
    cur.execute("""
        INSERT INTO article_history
        (title, content, updated_at, status, views, id_article, id_user)
        SELECT title, content, NOW(), 'published', views, id, %s
        FROM article
        WHERE id = %s
    """, (user_id, article_id))

    conn.commit()
    conn.close()