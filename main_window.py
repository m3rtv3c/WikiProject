from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget,
    QTableWidgetItem, QLineEdit,
    QLabel, QTextEdit, QMessageBox, QTextBrowser
)
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QIcon

from db import get_articles, get_article_by_id, get_article_by_title
from auth import LoginWindow


# ================= ARTICLE VIEW =================

class ArticleWindow(QWidget):
    def __init__(self, article):
        super().__init__()

        self.setWindowTitle(article["title"])
        self.resize(800, 600)

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(False)
        self.browser.anchorClicked.connect(self.handle_link)

        layout = QVBoxLayout()
        layout.addWidget(self.browser)
        self.setLayout(layout)

        self.load_article(article)

    # ================= LOAD ARTICLE =================

    def load_article(self, article):
        html = self.prepare_article(article)
        self.browser.setHtml(html)

    # ================= LINK HANDLER =================

    def handle_link(self, url: QUrl):
        title = url.toString()
        article = get_article_by_title(title)

        if article:
            self.setWindowTitle(article["title"])
            self.load_article(article)

    # ================= FORMAT ARTICLE =================

    def prepare_article(self, article):
        content = self.convert_wiki_links(article["content"])
        content = self.generate_toc(content)

        return f"""
        <html>
        <head>
        <style>
            body {{
                font-family: Arial;
                margin: 20px;
                background-color: #f8f9fa;
                line-height: 1.6;
            }}
            h1 {{
                border-bottom: 2px solid #ccc;
            }}
            h2 {{
                margin-top: 25px;
                border-bottom: 1px solid #ddd;
            }}
            .toc {{
                background: #ffffff;
                border: 1px solid #ccc;
                padding: 10px;
                width: 250px;
                margin-bottom: 20px;
            }}
            a {{
                color: #0645ad;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
        </style>
        </head>
        <body>
            <h1>{article['title']}</h1>
            {content}
        </body>
        </html>
        """

    # ================= WIKI LINKS [[Article]] =================

    def convert_wiki_links(self, text):
        import re

        pattern = r"\[\[(.*?)\]\]"

        def replace(match):
            title = match.group(1)
            return f'<a href="{title}">{title}</a>'

        return re.sub(pattern, replace, text)

    # ================= AUTO TOC =================

    def generate_toc(self, text):
        import re

        headers = re.findall(r"<h2>(.*?)</h2>", text)

        if not headers:
            return text

        toc = '<div class="toc"><b>Содержание</b><ul>'
        for h in headers:
            anchor = h.replace(" ", "_")
            text = text.replace(f"<h2>{h}</h2>", f'<h2 id="{anchor}">{h}</h2>')
            toc += f'<li><a href="#{anchor}">{h}</a></li>'

        toc += "</ul></div>"

        return toc + text

# ================= MAIN WINDOW =================

class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.user = None

        self.setWindowTitle("Wiki")
        self.resize(900, 600)
        self.setWindowIcon(QIcon('wiki.ico'))

        self.init_ui()
        self.load_articles()

    # ================= UI =================

    def init_ui(self):

        main = QVBoxLayout()
        top = QHBoxLayout()

        print(self.user)
        # --- Поиск ---
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск...")
        self.search.textChanged.connect(self.load_articles)

        # --- Пользователь ---
        self.user_label = QLabel("Гость")
        
        self.login_btn = QPushButton("Войти")
        self.login_btn.clicked.connect(self.open_login)

        # --- Кнопки ролей ---
        self.add_btn = QPushButton("Добавить")
        self.edit_btn = QPushButton("Редактировать")
        self.admin_btn = QPushButton("Админ панель")

        self.add_btn.clicked.connect(self.add_article)
        self.edit_btn.clicked.connect(self.edit_article)
        self.admin_btn.clicked.connect(self.open_admin_panel)

        # Скрываем по умолчанию
        self.add_btn.hide()
        self.edit_btn.hide()
        self.admin_btn.hide()

        # Добавляем в верхнюю панель
        top.addWidget(self.search)
        top.addWidget(self.user_label)
        top.addWidget(self.login_btn)
        top.addWidget(self.add_btn)
        top.addWidget(self.edit_btn)
        top.addWidget(self.admin_btn)

        # --- Таблица статей ---
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

    # ================= ROLE LOGIC =================

    def update_ui_by_role(self):

        self.add_btn.hide()
        self.edit_btn.hide()
        self.admin_btn.hide()

        if not self.user:
            return

        roles = self.user.get("roles", [])

        # ADMIN
        if "admin" in roles:
            self.add_btn.show()
            self.edit_btn.show()
            self.admin_btn.show()
            return

        # EDITOR
        if "editor" in roles:
            self.add_btn.show()
            self.edit_btn.show()

    # ================= LOGIN =================

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

            self.update_ui_by_role()

    def logout(self):
        self.user = None
        self.user_label.setText("Гость")

        self.login_btn.setText("Войти")
        self.login_btn.clicked.disconnect()
        self.login_btn.clicked.connect(self.open_login)

        self.update_ui_by_role()

    # ================= ARTICLES =================

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

    # ================= ACTIONS =================

    def add_article(self):
        if not self.user:
            QMessageBox.warning(self, "Ошибка", "Нет доступа")
            return

        roles = self.user.get("roles", [])
        if "admin" not in roles and "editor" not in roles:
            QMessageBox.warning(self, "Ошибка", "Нет прав")
            return

        QMessageBox.information(self, "INFO", "Открыть окно добавления статьи")

    def edit_article(self):
        if not self.user:
            QMessageBox.warning(self, "Ошибка", "Нет доступа")
            return

        roles = self.user.get("roles", [])
        if "admin" not in roles and "editor" not in roles:
            QMessageBox.warning(self, "Ошибка", "Нет прав")
            return

        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите статью")
            return

        article_id = int(self.table.item(row, 0).text())
        QMessageBox.information(self, "INFO", f"Редактирование статьи {article_id}")

    def open_admin_panel(self):
        if not self.user:
            return

        if "admin" not in self.user.get("roles", []):
            QMessageBox.warning(self, "Ошибка", "Нет прав администратора")
            return

        QMessageBox.information(self, "INFO", "Открыть админ панель")