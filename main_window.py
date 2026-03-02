from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget,
    QTableWidgetItem, QLineEdit,
    QLabel, QTextEdit
)

from db import get_articles, get_article_by_id
from auth import LoginWindow


class ArticleWindow(QWidget):
    def __init__(self, article):
        super().__init__()

        self.setWindowTitle(article["title"])
        self.resize(600, 400)

        layout = QVBoxLayout()

        text = QTextEdit()
        text.setReadOnly(True)
        text.setText(article["content"])

        layout.addWidget(text)
        self.setLayout(layout)


class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.user = None

        self.setWindowTitle("Wiki")
        self.resize(900, 600)

        self.init_ui()
        self.load_articles()

    def init_ui(self):

        main = QVBoxLayout()
        top = QHBoxLayout()

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск...")
        self.search.textChanged.connect(self.load_articles)

        self.user_label = QLabel("Гость")

        self.login_btn = QPushButton("Войти")
        self.login_btn.clicked.connect(self.open_login)

        top.addWidget(self.search)
        top.addWidget(self.user_label)
        top.addWidget(self.login_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Название", "Просмотры"]
        )
        self.table.setColumnHidden(0, True)
        self.table.cellDoubleClicked.connect(self.open_article)

        main.addLayout(top)
        main.addWidget(self.table)

        self.setLayout(main)

    # ---------- LOGIN ----------

    def open_login(self):
        dialog = LoginWindow()

        if dialog.exec_():
            self.user = dialog.user

            self.user_label.setText(
                f"Пользователь: {self.user['name']}"
            )

            self.login_btn.setText("Выход")
            self.login_btn.clicked.disconnect()
            self.login_btn.clicked.connect(self.logout)

    def logout(self):
        self.user = None
        self.user_label.setText("Гость")

        self.login_btn.setText("Войти")
        self.login_btn.clicked.disconnect()
        self.login_btn.clicked.connect(self.open_login)

    # ---------- ARTICLES ----------

    def load_articles(self):
        articles = get_articles(self.search.text())

        self.table.setRowCount(len(articles))

        for row, (id_, title, views) in enumerate(articles):
            self.table.setItem(row, 0, QTableWidgetItem(str(id_)))
            self.table.setItem(row, 1, QTableWidgetItem(title))
            self.table.setItem(row, 2, QTableWidgetItem(str(views)))

    def open_article(self, row, _):
        article_id = int(self.table.item(row, 0).text())

        article = get_article_by_id(article_id)

        if article:
            self.article_window = ArticleWindow(article)
            self.article_window.show()
