from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QFileDialog,
    QListWidget, QListWidgetItem, QHBoxLayout, QMessageBox, QTextBrowser,
    QTreeWidget, QTreeWidgetItem
)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt
from db import get_connection

class ArticleAddDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить статью")
        self.resize(1000, 600)

        self.images = []

        layout = QVBoxLayout()

        # Название статьи
        layout.addWidget(QLabel("Название статьи:"))
        self.title_edit = QLineEdit()
        layout.addWidget(self.title_edit)

        # Подсказка по Markdown
        layout.addWidget(QLabel(
            "Текст статьи (Markdown поддерживает):\n"
            "# Заголовок 1\n"
            "## Заголовок 2\n"
            "- Список\n"
            "```код```"
        ))

        # Горизонтальный layout: текст статьи + Preview + TOC
        content_layout = QHBoxLayout()

        # Текст статьи
        self.content_edit = QTextEdit()
        self.content_edit.textChanged.connect(self.update_preview)
        content_layout.addWidget(self.content_edit)

        # Preview + TOC
        right_layout = QVBoxLayout()

        # Live Preview
        self.preview_browser = QTextBrowser()
        self.preview_browser.setMinimumWidth(400)
        right_layout.addWidget(QLabel("Предпросмотр:"))
        right_layout.addWidget(self.preview_browser)

        # Древовидное оглавление
        self.toc_tree = QTreeWidget()
        self.toc_tree.setHeaderLabel("Оглавление")
        self.toc_tree.setMaximumWidth(250)
        right_layout.addWidget(QLabel("Оглавление:"))
        right_layout.addWidget(self.toc_tree)

        content_layout.addLayout(right_layout)
        layout.addLayout(content_layout)

        # Картинки
        layout.addWidget(QLabel("Картинки статьи:"))
        img_layout = QHBoxLayout()
        self.image_list = QListWidget()
        img_layout.addWidget(self.image_list)
        self.add_image_btn = QPushButton("Добавить картинку")
        self.add_image_btn.clicked.connect(self.add_image)
        img_layout.addWidget(self.add_image_btn)
        layout.addLayout(img_layout)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Добавить статью")
        self.save_btn.clicked.connect(self.save_article)
        self.cancel_btn = QPushButton("Закрыть")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    # ---------------- Добавление картинок ----------------
    def add_image(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Выберите картинки", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        for f in files:
            if f not in self.images:
                self.images.append(f)
                pixmap = QPixmap(f).scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                item = QListWidgetItem(f.split("/")[-1])
                item.setIcon(QIcon(pixmap))
                self.image_list.addItem(item)

    # ---------------- Live Preview + Древовидное TOC ----------------
    def update_preview(self):
        self.preview_browser.clear()
        self.toc_tree.clear()

        lines = self.content_edit.toPlainText().splitlines()
        in_list = False
        current_h1_item = None

        for line in lines:
            line = line.strip()

            # H1
            if line.startswith("# ") and not line.startswith("##"):
                if in_list:
                    self.preview_browser.append("</ul>")
                    in_list = False
                title = line[2:].strip()
                self.preview_browser.append(f"<h1>{title}</h1>")
                current_h1_item = QTreeWidgetItem([title])
                self.toc_tree.addTopLevelItem(current_h1_item)

            # H2
            elif line.startswith("## "):
                if in_list:
                    self.preview_browser.append("</ul>")
                    in_list = False
                title = line[3:].strip()
                self.preview_browser.append(f"<h2>{title}</h2>")
                if current_h1_item:
                    child_item = QTreeWidgetItem([title])
                    current_h1_item.addChild(child_item)
                else:
                    self.toc_tree.addTopLevelItem(QTreeWidgetItem([title]))

            # Список
            elif line.startswith("- "):
                if not in_list:
                    self.preview_browser.append("<ul>")
                    in_list = True
                self.preview_browser.append(f"<li>{line[2:].strip()}</li>")

            # Блок кода
            elif line.startswith("```") and line.endswith("```"):
                if in_list:
                    self.preview_browser.append("</ul>")
                    in_list = False
                self.preview_browser.append(f"<pre>{line[3:-3]}</pre>")

            # Обычный текст
            else:
                if in_list:
                    self.preview_browser.append("</ul>")
                    in_list = False
                self.preview_browser.append(f"<p>{line}</p>")

        if in_list:
            self.preview_browser.append("</ul>")

    # ---------------- Сохранение статьи ----------------
    def save_article(self):
        title = self.title_edit.text().strip()
        content = self.content_edit.toPlainText().strip()

        if not title or not content:
            QMessageBox.warning(self, "Ошибка", "Название и текст статьи обязательны")
            return

        try:
            conn = get_connection()
            cur = conn.cursor()

            # Вставка статьи
            cur.execute("""
                INSERT INTO article(title, content, status, views)
                VALUES (%s, %s, 'published', 0)
                RETURNING id
            """, (title, content))
            article_id = cur.fetchone()[0]

            # Вставка картинок
            for filepath in self.images:
                with open(filepath, "rb") as f:
                    img_bytes = f.read()
                cur.execute("""
                    INSERT INTO image(image_name, description) VALUES (%s, %s) RETURNING id
                """, (filepath.split("/")[-1], img_bytes))
                img_id = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO article_image(id_article, id_image) VALUES (%s, %s)
                """, (article_id, img_id))

            conn.commit()
            conn.close()
            QMessageBox.information(self, "Успешно", "Статья добавлена")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить статью:\n{e}")
            conn.rollback()
            conn.close()