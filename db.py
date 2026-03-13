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