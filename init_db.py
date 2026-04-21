import psycopg2
from psycopg2 import sql
from datetime import datetime

DB_NAME = "my_wiki"
DB_USER = "postgres"
DB_PASSWORD = "1234"
DB_HOST = "localhost"
DB_PORT = "5432"


def create_database():
    conn = psycopg2.connect(
        dbname="postgres",  # подключаемся к системной БД
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    conn.autocommit = True
    cur = conn.cursor()

    # проверяем существование базы
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    exists = cur.fetchone()

    if not exists:
        cur.execute(sql.SQL("CREATE DATABASE {}").format(
            sql.Identifier(DB_NAME)
        ))
        print("База данных создана")

    cur.close()
    conn.close()

def create_tables():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        login TEXT,
        password TEXT,
        reg_date TIMESTAMP,
        email TEXT,
        name TEXT
    );

    CREATE TABLE IF NOT EXISTS role (
        id SERIAL PRIMARY KEY,
        name TEXT,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS user_role (
        id SERIAL PRIMARY KEY,
        id_user INT REFERENCES users(id),
        id_role INT REFERENCES role(id)
    );

    CREATE TABLE IF NOT EXISTS article (
        id SERIAL PRIMARY KEY,
        title TEXT,
        content TEXT,
        created_at TIMESTAMP,
        status TEXT,
        views INT DEFAULT 0,
        id_user INT REFERENCES users(id),
        parent_id INT
    );

    CREATE TABLE IF NOT EXISTS article_history (
        id SERIAL PRIMARY KEY,
        title TEXT,
        content TEXT,
        updated_at TIMESTAMP,
        status TEXT,
        views INT,
        id_article INT REFERENCES article(id),
        id_user INT REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS image (
        id SERIAL PRIMARY KEY,
        image_name TEXT,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS article_image (
        id SERIAL PRIMARY KEY,
        id_article INT REFERENCES article(id),
        id_image INT REFERENCES image(id),
        id_history INT REFERENCES article_history(id)
    );
    """)

    conn.commit()
    cur.close()
    conn.close()

def init_db():
    create_database()
    create_tables()

def create_default_admin():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cur = conn.cursor()

    # 🔹 проверяем есть ли уже админ
    cur.execute("""
        SELECT u.id
        FROM users u
        JOIN user_role ur ON u.id = ur.id_user
        JOIN role r ON ur.id_role = r.id
        WHERE r.name = 'admin'
        LIMIT 1
    """)
    
    if cur.fetchone():
        cur.close()
        conn.close()
        return  # админ уже есть

    print("Создаём администратора...")

    # 🔹 создаём роль admin (если нет)
    cur.execute("""
        INSERT INTO role (name, description)
        VALUES ('admin', 'Администратор')
        RETURNING id
    """)
    role_id = cur.fetchone()

    if not role_id:
        cur.execute("SELECT id FROM role WHERE name = 'admin'")
        role_id = cur.fetchone()

    role_id = role_id[0]

    # 🔹 создаём пользователя
    cur.execute("""
        INSERT INTO users (login, password, reg_date, email, name)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (
        "admin",
        "admin", 
        datetime.now(),
        "admin@mail.com",
        "Администратор"
    ))

    user_id = cur.fetchone()[0]

    # 🔹 связываем с ролью
    cur.execute("""
        INSERT INTO user_role (id_user, id_role)
        VALUES (%s, %s)
    """, (user_id, role_id))

    conn.commit()
    cur.close()
    conn.close()

    print("Админ создан: login=admin, password=admin")