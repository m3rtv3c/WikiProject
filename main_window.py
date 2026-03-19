import re
from PyQt5.QtCore import pyqtSignal

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget,
    QTableWidgetItem, QLineEdit,
    QLabel, QMessageBox, QTextBrowser,
    QSizePolicy, QTreeWidget, QTreeWidgetItem,
    
)

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QIcon, QPixmap

from db import (
    get_articles,
    get_article_by_id,
    get_article_images,
    get_all_article_titles,
    get_article_by_title,
    increase_views
)

from auth import LoginWindow
from articleEditDialog import ArticleEditDialog


# ================= AUTO LINK =================
def auto_link_articles(text, titles):

    for title in sorted(titles, key=len, reverse=True):

        pattern = r'\b' + re.escape(title) + r'\b'

        text = re.sub(
            pattern,
            f'<a href="article:{title}">{title}</a>',
            text
        )

    return text


# ================= ARTICLE VIEW =================
class ArticleWindow(QWidget):
    article_viewed = pyqtSignal()

    def __init__(self, article):
        super().__init__()

        self.setWindowTitle(article["title"])
        self.resize(900, 600)

        self.all_titles = get_all_article_titles()

        self.history = []
        self.current_article = article

        # ================= MAIN LAYOUT =================
        main_layout = QVBoxLayout()
        nav_layout = QHBoxLayout()

        self.back_btn = QPushButton("<- Назад")
        self.back_btn.clicked.connect(self.go_back)
        self.back_btn.setEnabled(False)

        nav_layout.addWidget(self.back_btn)
        nav_layout.addStretch()

        main_layout.addLayout(nav_layout)
        top_layout = QHBoxLayout()

        # ---------------- IMAGE ----------------
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.image_label.setMaximumWidth(300)

        top_layout.addWidget(self.image_label)

        # ---------------- TOC ----------------
        self.toc_tree = QTreeWidget()
        self.toc_tree.setHeaderLabel("Оглавление")
        self.toc_tree.setMaximumWidth(250)

        top_layout.addWidget(self.toc_tree)

        main_layout.addLayout(top_layout)

        # ---------------- ARTICLE TEXT ----------------
        self.text_browser = QTextBrowser()

        self.text_browser.setOpenLinks(False)
        self.text_browser.anchorClicked.connect(self.open_link)

        main_layout.addWidget(self.text_browser)

        self.setLayout(main_layout)

        self.load_article(article)

        self.toc_tree.itemClicked.connect(self.scroll_to_anchor)

    # ---------------- OPEN LINK ----------------
    def open_link(self, url: QUrl):

        if url.scheme() == "article":

            title = url.path()

        article = get_article_by_title(title)

        if article:
            increase_views(article["id"])
            self.article_viewed.emit()
            # сохраняем текущую статью
            self.history.append(self.current_article)

            self.back_btn.setEnabled(True)

            # открываем новую
            self.current_article = article
            self.setWindowTitle(article["title"])
            self.load_article(article)

        else:
            QMessageBox.warning(self, "Ошибка", f"Статья '{title}' не найдена")

    def go_back(self):

        if not self.history:
            return

        article = self.history.pop()

        self.current_article = article
        self.setWindowTitle(article["title"])
        self.load_article(article)

        if not self.history:
            self.back_btn.setEnabled(False)

    # ---------------- SCROLL TO ANCHOR ----------------
    def scroll_to_anchor(self, item, column):

        anchor_name = item.data(0, Qt.UserRole)

        if anchor_name:
            self.text_browser.scrollToAnchor(anchor_name)

    # ---------------- LOAD ARTICLE ----------------
    def load_article(self, article):

        
   
        article_id = article.get("article_id", article["id"])
        images = get_article_images(article_id)

        if images:
            pixmap = QPixmap()
            pixmap.loadFromData(images[0])
            pixmap = pixmap.scaledToWidth(300, Qt.SmoothTransformation)
            self.image_label.setPixmap(pixmap)
        else:
            self.image_label.setText("Нет изображения")

        content = article["content"].split("\n")

        self.toc_tree.clear()

        html = ""

        current_h1_item = None
        anchor_counter = 0
        in_list = False

        for line in content:

            line = line.strip()

            if not line:
                continue

            anchor_counter += 1
            anchor_name = f"anchor_{anchor_counter}"

            # ---------------- H1 ----------------
            if line.startswith("# ") and not line.startswith("##"):

                if in_list:
                    html += "</ul>"
                    in_list = False

                title = line[2:].strip()

                html += f'<h1><a name="{anchor_name}"></a>{title}</h1>'

                current_h1_item = QTreeWidgetItem([title])
                current_h1_item.setData(0, Qt.UserRole, anchor_name)

                self.toc_tree.addTopLevelItem(current_h1_item)

            # ---------------- H2 ----------------
            elif line.startswith("## "):

                if in_list:
                    html += "</ul>"
                    in_list = False

                title = line[3:].strip()

                html += f'<h2><a name="{anchor_name}"></a>{title}</h2>'

                if current_h1_item:

                    child_item = QTreeWidgetItem([title])
                    child_item.setData(0, Qt.UserRole, anchor_name)

                    current_h1_item.addChild(child_item)

                else:

                    item = QTreeWidgetItem([title])
                    item.setData(0, Qt.UserRole, anchor_name)

                    self.toc_tree.addTopLevelItem(item)

            # ---------------- LIST ----------------
            elif line.startswith("- "):

                if not in_list:
                    html += "<ul>"
                    in_list = True

                text = auto_link_articles(line[2:].strip(), self.all_titles)

                html += f"<li>{text}</li>"

            # ---------------- CODE ----------------
            elif line.startswith("```") and line.endswith("```"):

                if in_list:
                    html += "</ul>"
                    in_list = False

                html += f"<pre>{line[3:-3]}</pre>"

            # ---------------- TEXT ----------------
            else:

                if in_list:
                    html += "</ul>"
                    in_list = False

                text = auto_link_articles(line, self.all_titles)

                html += f"<p>{text}</p>"

        if in_list:
            html += "</ul>"

        self.text_browser.setHtml(html)


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

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск...")
        self.search.textChanged.connect(self.load_articles)

        self.user_label = QLabel("Гость")

        self.login_btn = QPushButton("Войти")
        self.login_btn.clicked.connect(self.open_login)

        self.add_btn = QPushButton("Добавить")
        self.edit_btn = QPushButton("Редактировать")
        self.admin_btn = QPushButton("Админ панель")

        self.add_btn.clicked.connect(self.add_article)
        self.edit_btn.clicked.connect(self.edit_article)
        self.admin_btn.clicked.connect(self.open_admin_panel)

        self.add_btn.hide()
        self.edit_btn.hide()
        self.admin_btn.hide()

        top.addWidget(self.search)
        top.addWidget(self.user_label)
        top.addWidget(self.login_btn)
        top.addWidget(self.add_btn)
        top.addWidget(self.edit_btn)
        top.addWidget(self.admin_btn)

        self.table = QTableWidget()

        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Название", "Просмотры"])

        self.table.setColumnHidden(0, True)

        self.table.cellDoubleClicked.connect(self.open_article)

        main.addLayout(top)
        main.addWidget(self.table)

        self.setLayout(main)

    # ================= ROLE =================
    def update_ui_by_role(self):

        self.add_btn.hide()
        self.edit_btn.hide()
        self.admin_btn.hide()

        if not self.user:
            return

        roles = self.user.get("roles", [])

        if "admin" in roles:

            self.add_btn.show()
            self.edit_btn.show()
            self.admin_btn.show()

        elif "editor" in roles:

            self.add_btn.show()
            self.edit_btn.show()

    # ================= LOGIN =================
    def open_login(self):

        dialog = LoginWindow()

        if dialog.exec_():

            self.user = dialog.user

            self.user_label.setText(f"Пользователь: {self.user['name']}")

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
            increase_views(article_id) 
            self.load_articles()

            self.article_window = ArticleWindow(article)
            self.article_window.article_viewed.connect(self.load_articles)
            self.article_window.show()

    # ================= ACTIONS =================
    def add_article(self):
        # Проверка, что пользователь авторизован
        if not self.user or "id" not in self.user:
            QMessageBox.warning(self, "Ошибка", "Нет доступа")
            return

        # Проверка ролей
        roles = self.user.get("roles", [])
        if "admin" not in roles and "editor" not in roles:
            QMessageBox.warning(self, "Ошибка", "Нет прав")
            return

        # Импорт диалога
        from articleAddDialog import ArticleAddDialog

        # Создаем диалог, передавая корректный user_id
        dialog = ArticleAddDialog(user_id=self.user["id"], parent=self)

        # Если пользователь добавил статью — обновляем список
        if dialog.exec_():
            self.load_articles()

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

        dialog = ArticleEditDialog(article_id, user_id=self.user['id'], parent=self)
        if dialog.exec_():
         self.load_articles()

    def open_admin_panel(self):

        if not self.user:
            return

        if "admin" not in self.user.get("roles", []):
            QMessageBox.warning(self, "Ошибка", "Нет прав администратора")
            return

        from adminPanel import AdminPanel


        self.admin_window = AdminPanel()
        self.admin_window.destroyed.connect(self.load_articles)

        self.admin_window.show()