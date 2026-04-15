import re
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QFileDialog, QListWidget, QListWidgetItem, QMessageBox,
    QTextBrowser, QTreeWidget, QTreeWidgetItem
)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt

from db import (
    get_connection,
    get_article_by_id,
    get_article_images,
    get_all_article_titles
)

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
        self.user_id = user_id
        self.images = []
        self.all_titles = get_all_article_titles()

        layout = QVBoxLayout()

        # ================= TITLE =================
        layout.addWidget(QLabel("Название статьи:"))
        self.title_edit = QLineEdit()
        layout.addWidget(self.title_edit)

        # ================= CONTENT =================
        layout.addWidget(QLabel("Текст статьи:"))
        self.content_edit = QTextEdit()
        self.content_edit.textChanged.connect(self.update_preview)
        layout.addWidget(self.content_edit)

        # ================= PREVIEW =================
        layout.addWidget(QLabel("Предпросмотр:"))
        self.preview_browser = QTextBrowser()
        layout.addWidget(self.preview_browser)

        # ================= TOC =================
        layout.addWidget(QLabel("Оглавление:"))
        self.toc_tree = QTreeWidget()
        self.toc_tree.setHeaderLabel("Оглавление")
        layout.addWidget(self.toc_tree)

        # ================= IMAGES =================
        layout.addWidget(QLabel("Картинки статьи:"))
        img_layout = QHBoxLayout()

        self.image_list = QListWidget()
        img_layout.addWidget(self.image_list)

        btns_layout = QVBoxLayout()

        self.add_image_btn = QPushButton("Добавить")
        self.add_image_btn.clicked.connect(self.add_image)

        self.remove_image_btn = QPushButton("Удалить")
        self.remove_image_btn.clicked.connect(self.remove_image)

        self.replace_image_btn = QPushButton("Заменить")
        self.replace_image_btn.clicked.connect(self.replace_image)

        btns_layout.addWidget(self.add_image_btn)
        btns_layout.addWidget(self.remove_image_btn)
        btns_layout.addWidget(self.replace_image_btn)

        img_layout.addLayout(btns_layout)
        layout.addLayout(img_layout)

        # ================= BUTTONS =================
        btn_layout = QHBoxLayout()

        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.save_article)

        self.cancel_btn = QPushButton("Закрыть")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.load_article()

    # ================= LOAD =================
    def load_article(self):
        article = get_article_by_id(self.article_id)
        if not article:
            QMessageBox.critical(self, "Ошибка", "Статья не найдена")
            self.reject()
            return

        self.title_edit.setText(article["title"])
        self.content_edit.setPlainText(article["content"])

        images = get_article_images(self.article_id)
        for idx, img_bytes in enumerate(images):
            pixmap = QPixmap()
            pixmap.loadFromData(img_bytes)

            pixmap = pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            item = QListWidgetItem(f"image_{idx+1}")
            item.setIcon(QIcon(pixmap))

            self.image_list.addItem(item)
            self.images.append(img_bytes)

        self.update_preview()

    # ================= IMAGES =================
    def add_image(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Выберите картинки", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )

        for f in files:
            with open(f, "rb") as file:
                self.images.append(file.read())

            pixmap = QPixmap(f).scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            item = QListWidgetItem(f.split("/")[-1])
            item.setIcon(QIcon(pixmap))

            self.image_list.addItem(item)

    def remove_image(self):
        row = self.image_list.currentRow()
        if row >= 0:
            self.image_list.takeItem(row)
            self.images.pop(row)

    def replace_image(self):
        row = self.image_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите картинку")
            return

        file, _ = QFileDialog.getOpenFileName(
            self, "Выберите картинку", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )

        if file:
            self.images[row] = file

            pixmap = QPixmap(file).scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            item = self.image_list.item(row)
            item.setIcon(QIcon(pixmap))
            item.setText(file.split("/")[-1])

    # ================= PREVIEW =================
    def update_preview(self):
        self.preview_browser.clear()
        self.toc_tree.clear()

        lines = self.content_edit.toPlainText().splitlines()

        html = ""
        in_list = False
        current_h1 = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("# "):
                html += f"<h1>{line[2:]}</h1>"
                current_h1 = QTreeWidgetItem([line[2:]])
                self.toc_tree.addTopLevelItem(current_h1)

            elif line.startswith("## "):
                html += f"<h2>{line[3:]}</h2>"
                if current_h1:
                    current_h1.addChild(QTreeWidgetItem([line[3:]]))

            elif line.startswith("- "):
                if not in_list:
                    html += "<ul>"
                    in_list = True

                text = auto_link_articles(line[2:], self.all_titles)
                html += f"<li>{text}</li>"

            else:
                if in_list:
                    html += "</ul>"
                    in_list = False

                text = auto_link_articles(line, self.all_titles)
                html += f"<p>{text}</p>"

        if in_list:
            html += "</ul>"

        self.preview_browser.setHtml(html)

    # ================= SAVE =================
    def save_article(self):
        title = self.title_edit.text().strip()
        content = self.content_edit.toPlainText().strip()

        if not title or not content:
            QMessageBox.warning(self, "Ошибка", "Пустые поля")
            return

        conn = None

        try:
            conn = get_connection()
            cur = conn.cursor()

            cur.execute("SET LOCAL myapp.current_user_id = %s", (self.user_id,))

            cur.execute("""
                INSERT INTO article_history (id_article, title, content, status, id_user)
                VALUES (%s, %s, %s, 'pending', %s)
                RETURNING id
            """, (self.article_id, title, content, self.user_id))

            history_id = cur.fetchone()[0]

            # ================= IMAGES =================
            for i, img in enumerate(self.images, start=1):
                img_bytes = img

                cur.execute("""
                    INSERT INTO image (image_name, description)
                    VALUES (%s, %s)
                    RETURNING id
                """, (f"image_{i}", img_bytes))

                img_id = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO article_image (id_history, id_image)
                    VALUES (%s, %s)
                """, (history_id, img_id))

            conn.commit()
            conn.close()

            QMessageBox.information(self, "Успех", "Отправлено на модерацию")
            self.accept()

        except Exception as e:
            if conn:
                conn.rollback()
                conn.close()

            QMessageBox.critical(self, "Ошибка", str(e))