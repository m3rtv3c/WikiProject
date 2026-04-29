import re
from PyQt5.QtCore import pyqtSignal, Qt, QUrl
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLineEdit, QLabel, QMessageBox, QTextBrowser,
    QSizePolicy, QTreeWidget, QTreeWidgetItem, QHeaderView, QSplitter,
    QFrame
)
from PyQt5.QtGui import QIcon, QPixmap, QFont
from db import (
    get_articles, get_article_by_id, get_article_images,
    get_all_article_titles, get_article_by_title, increase_views
)
from auth import LoginWindow
from articleEditDialog import ArticleEditDialog

# ================= MODERN THEME (QSS) =================
MODERN_THEME = """
QWidget {
    font-family: "Segoe UI", "Roboto", "Arial", sans-serif;
    font-size: 13px;
    color: #1f2937;
    background-color: #f8fafc;
}
QPushButton {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    color: #334155;
}
QPushButton:hover { background-color: #f1f5f9; border-color: #94a3b8; }
QPushButton:pressed { background-color: #e2e8f0; }
QPushButton:disabled { background-color: #f8fafc; color: #94a3b8; border-color: #e2e8f0; }

QLineEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px 12px;
}
QLineEdit:focus { border-color: #3b82f6; }

QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    gridline-color: #f1f5f9;
    selection-background-color: #dbeafe;
    selection-color: #1e3a8a;
}
QHeaderView::section {
    background-color: #f8fafc;
    border: none;
    border-bottom: 2px solid #e2e8f0;
    padding: 10px;
    font-weight: 600;
    color: #475569;
}
QTableWidget::item { padding: 10px; }
QTableWidget::item:hover { background-color: #f8fafc; }

QTreeWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 6px;
}
QTreeWidget::item { padding: 8px 10px; border-radius: 4px; }
QTreeWidget::item:hover { background-color: #f0f9ff; }
QTreeWidget::item:selected { background-color: #dbeafe; color: #1e40af; }

QTextBrowser {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 20px;
    font-size: 14px;
    line-height: 1.65;
}
QTextBrowser h1 { font-size: 24px; margin: 24px 0 12px 0; color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }
QTextBrowser h2 { font-size: 20px; margin: 20px 0 10px 0; color: #1e293b; }
QTextBrowser p { margin: 8px 0; }
QTextBrowser a { color: #2563eb; text-decoration: none; font-weight: 500; }
QTextBrowser a:hover { color: #1d4ed8; text-decoration: underline; }
QTextBrowser pre { background: #f8fafc; padding: 12px; border-radius: 6px; border: 1px solid #e2e8f0; font-family: monospace; font-size: 13px; }
QTextBrowser ul { margin-left: 24px; }
QTextBrowser li { margin-bottom: 4px; }

QLabel { background-color: transparent; }
QSplitter::handle { background-color: #cbd5e1; height: 2px; }
"""

# ================= AUTO LINK =================
def auto_link_articles(text, titles, current_title):
    for title in sorted(titles, key=len, reverse=True):
        if title == current_title:
            continue
        pattern = r'\b' + re.escape(title) + r'\b'
        text = re.sub(pattern, f'<a href="article:{title}">{title}</a>', text)
    return text

# ================= ARTICLE VIEW =================
class ArticleWindow(QWidget):
    article_viewed = pyqtSignal()

    def __init__(self, article):
        super().__init__()
        self.setWindowTitle(article["title"])
        self.resize(1000, 650)
        self.setStyleSheet(MODERN_THEME)

        self.all_titles = get_all_article_titles()
        self.history = []
        self.current_article = article

        # ================= MAIN LAYOUT =================
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Top Navigation
        nav_layout = QHBoxLayout()
        self.back_btn = QPushButton("← Назад")
        self.back_btn.setFixedWidth(90)
        self.back_btn.clicked.connect(self.go_back)
        self.back_btn.setEnabled(False)

        self.title_label = QLabel(article["title"])
        self.title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.title_label.setStyleSheet("color: #0f172a; padding-left: 10px;")

        nav_layout.addWidget(self.back_btn)
        nav_layout.addWidget(self.title_label, 1)
        main_layout.addLayout(nav_layout)

        # Content Splitter (TOC + Image | Text)
        content_splitter = QSplitter(Qt.Horizontal)
        left_panel = QVBoxLayout()

        # Image
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.image_label.setMaximumHeight(250)
        self.image_label.setStyleSheet("background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px;")
        left_panel.addWidget(self.image_label)

        # TOC
        self.toc_tree = QTreeWidget()
        self.toc_tree.setHeaderLabel("📑 Оглавление")
        self.toc_tree.setMinimumWidth(220)
        left_panel.addLayout(left_panel)
        
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        content_splitter.addWidget(left_widget)

        # Text
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenLinks(False)
        self.text_browser.anchorClicked.connect(self.open_link)
        content_splitter.addWidget(self.text_browser)
        
        content_splitter.setStretchFactor(0, 1)
        content_splitter.setStretchFactor(1, 3)
        main_layout.addWidget(content_splitter)

        self.setLayout(main_layout)
        self.load_article(article)
        self.toc_tree.itemClicked.connect(self.scroll_to_anchor)

    # ---------------- OPEN LINK ----------------
    def open_link(self, url: QUrl):
        if url.scheme() == "article":
            title = url.path()
        else:
            return

        article = get_article_by_title(title)
        if article:
            increase_views(article["id"])
            self.article_viewed.emit()
            self.history.append(self.current_article)
            self.back_btn.setEnabled(True)

            self.current_article = article
            self.setWindowTitle(article["title"])
            self.title_label.setText(article["title"])
            self.load_article(article)
        else:
            QMessageBox.warning(self, "Ошибка", f"Статья '{title}' не найдена")

    def go_back(self):
        if not self.history:
            return
        article = self.history.pop()
        self.current_article = article
        self.setWindowTitle(article["title"])
        self.title_label.setText(article["title"])
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
            pixmap = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
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

            if line.startswith("# ") and not line.startswith("##"):
                if in_list: html += "</ul>"; in_list = False
                title = line[2:].strip()
                html += f'<h1><a name="{anchor_name}"></a>{title}</h1>'
                current_h1_item = QTreeWidgetItem([title])
                current_h1_item.setData(0, Qt.UserRole, anchor_name)
                self.toc_tree.addTopLevelItem(current_h1_item)

            elif line.startswith("## "):
                if in_list: html += "</ul>"; in_list = False
                title = line[3:].strip()
                html += f'<h2><a name="{anchor_name}"></a>{title}</h2>'
                child_item = QTreeWidgetItem([title])
                child_item.setData(0, Qt.UserRole, anchor_name)
                if current_h1_item:
                    current_h1_item.addChild(child_item)
                else:
                    item = QTreeWidgetItem([title])
                    item.setData(0, Qt.UserRole, anchor_name)
                    self.toc_tree.addTopLevelItem(item)

            elif line.startswith("- "):
                if not in_list: html += "<ul>"; in_list = True
                text = auto_link_articles(line[2:].strip(), self.all_titles, article["title"])
                html += f"<li>{text}</li>"

            elif line.startswith("```") and line.endswith("```"):
                if in_list: html += "</ul>"; in_list = False
                html += f"<pre>{line[3:-3]}</pre>"

            else:
                if in_list: html += "</ul>"; in_list = False
                text = auto_link_articles(line, self.all_titles, article["title"])
                html += f"<p>{text}</p>"

        if in_list:
            html += "</ul>"

        self.text_browser.setHtml(html)


# ================= MAIN WINDOW =================
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wiki")
        self.resize(950, 600)
        self.setWindowIcon(QIcon('wiki.ico'))
        self.setStyleSheet(MODERN_THEME)
        self.user = None

        self.init_ui()
        self.load_articles()

    # ================= UI =================
    def init_ui(self):
        main = QVBoxLayout()
        main.setContentsMargins(16, 16, 16, 16)
        main.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(10)

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Поиск по названию...")
        self.search.textChanged.connect(self.load_articles)

        self.user_label = QLabel("👤 Гость")
        self.user_label.setStyleSheet("color: #64748b; font-weight: 500;")

        self.login_btn = QPushButton("Войти")
        self.login_btn.clicked.connect(self.open_login)

        self.add_btn = QPushButton("+ Добавить")
        self.edit_btn = QPushButton("✏️ Редактировать")
        self.admin_btn = QPushButton("⚙️ Админ панель")

        self.add_btn.clicked.connect(self.add_article)
        self.edit_btn.clicked.connect(self.edit_article)
        self.admin_btn.clicked.connect(self.open_admin_panel)

        self.add_btn.hide()
        self.edit_btn.hide()
        self.admin_btn.hide()

        top.addWidget(self.search, 2)
        top.addWidget(self.user_label)
        top.addWidget(self.login_btn)
        top.addWidget(self.add_btn)
        top.addWidget(self.edit_btn)
        top.addWidget(self.admin_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Название", "Просмотры"])
        self.table.setColumnHidden(0, True)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.cellDoubleClicked.connect(self.open_article)
        
        # Header styling
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 100)

        main.addLayout(top)
        main.addWidget(self.table, 1)
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
            self.user_label.setText(f"👤 {self.user['name']}")
            self.login_btn.setText("Выход")
            self.login_btn.clicked.disconnect()
            self.login_btn.clicked.connect(self.logout)
            self.update_ui_by_role()

    def logout(self):
        self.user = None
        self.user_label.setText("👤 Гость")
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
        if not self.user or "id" not in self.user:
            QMessageBox.warning(self, "Ошибка", "Нет доступа")
            return
        roles = self.user.get("roles", [])
        if "admin" not in roles and "editor" not in roles:
            QMessageBox.warning(self, "Ошибка", "Нет прав")
            return
        from articleAddDialog import ArticleAddDialog
        dialog = ArticleAddDialog(user_id=self.user["id"], parent=self)
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
        if not self.user or "admin" not in self.user.get("roles", []):
            QMessageBox.warning(self, "Ошибка", "Нет прав администратора")
            return
        from adminPanel import AdminPanel
        self.admin_window = AdminPanel()
        self.admin_window.data_changed.connect(self.load_articles)
        self.admin_window.show()
    
    def closeEvent(self, event):
        self.article_viewed.emit()
        super().closeEvent(event)  # Исправлена ошибка вызова super