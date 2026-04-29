import hashlib
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QMessageBox
)
from db import get_user_with_roles, create_user


# ================= ХЕШИРОВАНИЕ (ВСТРОЕННОЕ) =================
def hash_password(password: str) -> str:
    """Создаёт хеш с уникальной солью и 100k итераций"""
    salt = os.urandom(16).hex()
    pwd_hash = hashlib.pbkdf2_hmac(
        'sha256', 
        password.encode('utf-8'), 
        salt.encode('utf-8'), 
        100_000
    )
    return f"{salt}${pwd_hash.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Проверяет plain-текст пароль против сохранённого хеша"""
    try:
        salt, hash_hex = stored_hash.split('$')
        new_hash = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt.encode('utf-8'), 
            100_000
        )
        return new_hash.hex() == hash_hex
    except (ValueError, AttributeError):
        return False


# ================= REGISTRATION =================
class RegistrationWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Регистрация")
        self.setFixedSize(300, 260)
        self.setModal(True)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.login = QLineEdit()
        self.email = QLineEdit()
        self.name = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)

        form.addRow("Login:", self.login)
        form.addRow("Email:", self.email)
        form.addRow("Name:", self.name)
        form.addRow("Password:", self.password)

        self.register_btn = QPushButton("Создать аккаунт")
        layout.addLayout(form)
        layout.addWidget(self.register_btn)
        self.setLayout(layout)

        self.register_btn.clicked.connect(self.register)

    def register(self):
        if not all([self.login.text(), self.email.text(), self.name.text(), self.password.text()]):
            QMessageBox.warning(self, "Ошибка", "Заполните все поля")
            return

        # 🔐 Хешируем пароль перед записью в БД
        pwd_hash = hash_password(self.password.text())

        create_user(
            self.login.text(),
            pwd_hash,  # В БД попадает только хеш
            self.name.text(),
            self.email.text()
        )

        QMessageBox.information(self, "OK", "Пользователь создан")
        self.accept()


# ================= LOGIN =================
class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.user = None

        self.setWindowTitle("Авторизация")
        self.setFixedSize(300, 180)
        self.setModal(True)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.login = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)

        form.addRow("Login:", self.login)
        form.addRow("Password:", self.password)

        self.login_btn = QPushButton("Войти")
        self.register_btn = QPushButton("Регистрация")

        layout.addLayout(form)
        layout.addWidget(self.login_btn)
        layout.addWidget(self.register_btn)
        self.setLayout(layout)

        self.login_btn.clicked.connect(self.login_user)
        self.register_btn.clicked.connect(self.open_register)

    def login_user(self):
        login = self.login.text().strip()
        password = self.password.text()

        if not login or not password:
            QMessageBox.warning(self, "Ошибка", "Введите логин и пароль")
            return

        # ✅ Запрашиваем только по логину
        user_data = get_user_with_roles(login)

        # ✅ Проверяем пароль на стороне Python
        if user_data and verify_password(password, user_data["password_hash"]):
            self.user = user_data
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", "Неверный логин или пароль")

    def open_register(self):
        reg = RegistrationWindow()
        reg.exec_()