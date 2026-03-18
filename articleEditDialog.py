import re
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QFileDialog, QListWidget, QListWidgetItem, QMessageBox,
    QTextBrowser, QTreeWidget, QTreeWidgetItem
)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt

from db import get_connection, get_article_by_id, get_article_images, get_all_article_titles


# ================= AUTO LINK =================
def auto_link_articles(text, titles):
    for title in sorted(titles, key=len, reverse=True):
        pattern = r'\b' + re.escape(title) + r'\b'
        text = re.sub(pattern, f'<a href="#">{title}</a>', text)
    return text


# ================= ARTICLE EDIT DIALOG =================
class ArticleEditDialog(QDialog):
    def __init__(self, article_id, user_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактировать статью")
        self.resize(1000, 600)

        self.article_id = article_id
        self.user_id = user_id  # id пользователя, который редактирует
        self.images = []
        self.all_titles = get_all_article_titles()

        layout = QVBoxLayout()

        # ================= TITLE =================
        layout.addWidget(QLabel("Название статьи:"))
        self.title_edit = QLineEdit()
        layout.addWidget(self.title_edit)

        # ================= MARKDOWN HELP =================
        layout.addWidget(QLabel(
            "Текст статьи (Markdown поддерживает):\n"
            "# Заголовок 1\n"
            "## Заголовок 2\n"
            "- Список\n"
            "```код```"
        ))

        # ================= CONTENT AREA =================
        content_layout = QHBoxLayout()

        # ---------------- TEXT ----------------
        self.content_edit = QTextEdit()
        self.content_edit.textChanged.connect(self.update_preview)
        content_layout.addWidget(self.content_edit)

        # ---------------- PREVIEW + TOC ----------------
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Предпросмотр:"))

        self.preview_browser = QTextBrowser()
        self.preview_browser.setMinimumWidth(400)
        right_layout.addWidget(self.preview_browser)

        right_layout.addWidget(QLabel("Оглавление:"))
        self.toc_tree = QTreeWidget()
        self.toc_tree.setHeaderLabel("Оглавление")
        self.toc_tree.setMaximumWidth(250)
        right_layout.addWidget(self.toc_tree)

        content_layout.addLayout(right_layout)
        layout.addLayout(content_layout)

        # ================= IMAGES =================
        layout.addWidget(QLabel("Картинки статьи:"))
        img_layout = QHBoxLayout()
        self.image_list = QListWidget()
        img_layout.addWidget(self.image_list)
        self.add_image_btn = QPushButton("Добавить картинку")
        self.add_image_btn.clicked.connect(self.add_image)
        img_layout.addWidget(self.add_image_btn)
        layout.addLayout(img_layout)

        # ================= BUTTONS =================
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить изменения")
        self.save_btn.clicked.connect(self.save_article)
        self.cancel_btn = QPushButton("Закрыть")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # ================= LOAD ARTICLE =================
        self.load_article()

    def load_article(self):
        article = get_article_by_id(self.article_id)
        if not article:
            QMessageBox.critical(self, "Ошибка", "Статья не найдена")
            self.reject()
            return

        self.title_edit.setText(article["title"])
        self.content_edit.setPlainText(article["content"])

        # Загружаем картинки
        images = get_article_images(self.article_id)
        for idx, img_bytes in enumerate(images):
            pixmap = QPixmap()
            pixmap.loadFromData(img_bytes)
            pixmap = pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            item = QListWidgetItem(f"image_{idx+1}")
            item.setIcon(QIcon(pixmap))
            self.image_list.addItem(item)
            self.images.append(img_bytes)  # сохраняем img_bytes, чтобы не перезаписывать файлы

        self.update_preview()

    def add_image(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Выберите картинки", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        for f in files:
            if f not in self.images:
                self.images.append(f)
                pixmap = QPixmap(f).scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                item = QListWidgetItem(f.split("/")[-1])
                item.setIcon(QIcon(pixmap))
                self.image_list.addItem(item)

    def update_preview(self):
        self.preview_browser.clear()
        self.toc_tree.clear()
        lines = self.content_edit.toPlainText().splitlines()
        html = ""
        in_list = False
        current_h1_item = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # H1
            if line.startswith("# ") and not line.startswith("##"):
                if in_list:
                    html += "</ul>"
                    in_list = False
                title = line[2:].strip()
                html += f"<h1>{title}</h1>"
                current_h1_item = QTreeWidgetItem([title])
                self.toc_tree.addTopLevelItem(current_h1_item)
            # H2
            elif line.startswith("## "):
                if in_list:
                    html += "</ul>"
                    in_list = False
                title = line[3:].strip()
                html += f"<h2>{title}</h2>"
                if current_h1_item:
                    child_item = QTreeWidgetItem([title])
                    current_h1_item.addChild(child_item)
                else:
                    self.toc_tree.addTopLevelItem(QTreeWidgetItem([title]))
            # LIST
            elif line.startswith("- "):
                if not in_list:
                    html += "<ul>"
                    in_list = True
                text = auto_link_articles(line[2:].strip(), self.all_titles)
                html += f"<li>{text}</li>"
            # CODE
            elif line.startswith("```") and line.endswith("```"):
                if in_list:
                    html += "</ul>"
                    in_list = False
                html += f"<pre>{line[3:-3]}</pre>"
            else:
                if in_list:
                    html += "</ul>"
                    in_list = False
                text = auto_link_articles(line, self.all_titles)
                html += f"<p>{text}</p>"
        if in_list:
            html += "</ul>"
        self.preview_browser.setHtml(html)

    def save_article(self):
        title = self.title_edit.text().strip()
        content = self.content_edit.toPlainText().strip()

        if not title or not content:
            QMessageBox.warning(self, "Ошибка", "Название и текст статьи обязательны")
            return

        if not hasattr(self, "user_id") or self.user_id is None:
            QMessageBox.warning(self, "Ошибка", "Неизвестный пользователь")
            return

        conn = None

        try:
            conn = get_connection()
            cur = conn.cursor()

            # Передаём user_id в триггер (если используется)
            cur.execute("SET LOCAL myapp.current_user_id = %s", (self.user_id,))

            # ================= СОЗДАЁМ НОВУЮ ВЕРСИЮ =================
            cur.execute("""
                INSERT INTO article (title, content, status, parent_id)
                VALUES (%s, %s, 'pending', %s)
                RETURNING id
            """, (title, content, self.article_id))

            new_article_id = cur.fetchone()[0]

            # ================= КАРТИНКИ =================
            for i, img in enumerate(self.images, start=1):
                if isinstance(img, str):  # путь к файлу
                    with open(img, "rb") as f:
                        img_bytes = f.read()
                else:  # уже байты из БД
                    img_bytes = img

            # сохраняем картинку
                cur.execute("""
                    INSERT INTO image (image_name, description)
                    VALUES (%s, %s)
                    RETURNING id
                """, (f"image_{i}", img_bytes))

                img_id = cur.fetchone()[0]

                # связываем с новой статьёй
                cur.execute("""
                    INSERT INTO article_image (id_article, id_image)
                    VALUES (%s, %s)
                """, (new_article_id, img_id))

            conn.commit()
            conn.close()

            QMessageBox.information(
                self,
                "Успешно",
                "Изменения отправлены на модерацию (создана новая версия)"
            )
            self.accept()

        except Exception as e:
            if conn:
                conn.rollback()
                conn.close()

            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось сохранить статью:\n{e}"
            )