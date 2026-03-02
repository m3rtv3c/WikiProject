from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QMessageBox
)

from db import get_user_with_roles, create_user


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
        if not all([
            self.login.text(),
            self.email.text(),
            self.name.text(),
            self.password.text()
        ]):
            QMessageBox.warning(self, "Ошибка", "Заполните все поля")
            return

        create_user(
            self.login.text(),
            self.password.text(),
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
        user = get_user_with_roles(
            self.login.text(),
            self.password.text()
        )

        if user:
            self.user = user
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", "Неверный логин или пароль")

    def open_register(self):
        reg = RegistrationWindow()
        reg.exec_()