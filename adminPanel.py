import difflib

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QLabel,
    QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal

from db import (
    get_users,
    get_user_roles,
    set_user_role,
    get_full_history,
    get_history_by_id,
    has_new_history
)


class AdminPanel(QWidget):
    data_changed = pyqtSignal()
    def __init__(self, on_close=None):
        super().__init__()

        self.on_close = on_close

        from PyQt5.QtCore import Qt
        self.setAttribute(Qt.WA_DeleteOnClose)  # 🔥 ВОТ ЭТО КЛЮЧ  
        self.selected_history_id = None

        self.setWindowTitle("Админ панель")
        self.resize(1100, 600)
        self.showing_pending = False

        main_layout = QHBoxLayout()

        # ================= LEFT =================
        left = QVBoxLayout()

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск по статьям...")
        self.search.textChanged.connect(self.load_articles)
        left.addWidget(self.search)

        left.addWidget(QLabel("Пользователи"))
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(3)
        self.user_table.setHorizontalHeaderLabels(["ID", "Имя", "Роли"])
        left.addWidget(self.user_table)

        btns = QHBoxLayout()
        self.btn_admin = QPushButton("Admin")
        self.btn_editor = QPushButton("Editor")
        self.btn_user = QPushButton("User")
        self.btn_admin.clicked.connect(lambda: self.change_role("admin"))
        self.btn_editor.clicked.connect(lambda: self.change_role("editor"))
        self.btn_user.clicked.connect(lambda: self.change_role("user"))
        btns.addWidget(self.btn_admin)
        btns.addWidget(self.btn_editor)
        btns.addWidget(self.btn_user)
        left.addLayout(btns)

        left.addWidget(QLabel("Статьи"))
        self.article_table = QTableWidget()
        self.article_table.setColumnCount(4)
        self.article_table.setHorizontalHeaderLabels(
            ["ID", "Название", "Просмотры", "Статус"]
        )
        self.article_table.cellClicked.connect(self.load_history)
        self.article_table.cellDoubleClicked.connect(self.open_article_preview)
        
        left.addWidget(self.article_table)

        # кнопки статьи
        self.delete_btn = QPushButton("Удалить статью")
        self.delete_btn.clicked.connect(self.delete_article_ui)
        self.approve_add_btn = QPushButton("Одобрить добавление")
        self.approve_add_btn.clicked.connect(self.approve_new_article)
        left.addWidget(self.delete_btn)
        left.addWidget(self.approve_add_btn)  # 🔥 новая кнопка

        main_layout.addLayout(left, 1)

        # ================= RIGHT =================
        right = QVBoxLayout()
        right.addWidget(QLabel("История статьи"))
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "ID", "Название", "Дата", "Статус", "Просмотры", "Автор"
        ])
        self.history_table.cellDoubleClicked.connect(self.open_version)
        right.addWidget(self.history_table)

        self.approve_btn = QPushButton("Одобрить")
        self.reject_btn = QPushButton("Отклонить")
        self.rollback_btn = QPushButton("Откатить версию")
        self.approve_btn.clicked.connect(self.approve_article)
        self.reject_btn.clicked.connect(self.reject_article)
        self.rollback_btn.clicked.connect(self.rollback_version)

        right.addWidget(self.approve_btn)
        right.addWidget(self.reject_btn)
        right.addWidget(self.rollback_btn)

        main_layout.addLayout(right, 2)

        self.setLayout(main_layout)
        self.load_users()
        self.load_articles()

    # ================== APPROVE NEW ARTICLE ==================
    def approve_new_article(self):
        row = self.article_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выбери статью")
            return

        article_id = int(self.article_table.item(row, 0).text())
        confirm = QMessageBox.question(
            self,
            "Подтверждение",
            "Одобрить добавление этой статьи?"
        )
        if confirm != QMessageBox.Yes:
            return

        from db import approve_new_article  # нужно реализовать в db

        approve_new_article(article_id, getattr(self, "user_id", None))
        QMessageBox.information(self, "OK", "Статья одобрена и опубликована")
        self.load_articles()

    # ================= USERS =================
    def load_users(self):
        users = get_users()
        self.user_table.setRowCount(len(users))

        for row, (uid, name) in enumerate(users):
            roles = ", ".join(get_user_roles(uid))

            self.user_table.setItem(row, 0, QTableWidgetItem(str(uid)))
            self.user_table.setItem(row, 1, QTableWidgetItem(name))
            self.user_table.setItem(row, 2, QTableWidgetItem(roles))

    def change_role(self, role):
        row = self.user_table.currentRow()

        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выбери пользователя")
            return

        uid = int(self.user_table.item(row, 0).text())
        set_user_role(uid, role)
        self.load_users()

    # ================= ARTICLES =================
    def load_articles(self):
        from db import get_all_articles

        self.showing_pending = False

        articles = get_all_articles(self.search.text())
        self.article_table.setRowCount(len(articles))

        for row, (id_, title, views, status) in enumerate(articles):
            self.article_table.setItem(row, 0, QTableWidgetItem(str(id_)))
            self.article_table.setItem(row, 1, QTableWidgetItem(title))
            self.article_table.setItem(row, 2, QTableWidgetItem(str(views)))
            self.article_table.setItem(row, 3, QTableWidgetItem(status))

            color = None

            article_id = int(id_)

            if has_new_history(article_id):
                color = Qt.yellow  # есть новые версии (НЕ применённые / есть изменения)
            elif status == "published":
                color = Qt.green
            elif status == "pending":
                color = Qt.lightGray
            elif status == "rejected":
                color = Qt.darkRed
            elif status == "deleted":
                color = Qt.red

            if color:
                for col in range(4):
                    self.article_table.item(row, col).setBackground(color)

    # ================= HISTORY =================
    def load_history(self, row, col):
        article_id = int(self.article_table.item(row, 0).text())
        data = get_full_history(article_id)
        selected_id = getattr(self, "selected_history_id", None)

        self.history_table.setRowCount(len(data))

        for row_i, (hid, title, date, status, views, user, article_id) in enumerate(data):
            item = QTableWidgetItem(str(hid))
            item.setData(Qt.UserRole, article_id)
            self.history_table.setItem(row_i, 0, item)

            self.history_table.setItem(row_i, 1, QTableWidgetItem(title))
            self.history_table.setItem(row_i, 2, QTableWidgetItem(str(date)))
            self.history_table.setItem(row_i, 3, QTableWidgetItem(status))
            self.history_table.setItem(row_i, 4, QTableWidgetItem(str(views)))
            self.history_table.setItem(row_i, 5, QTableWidgetItem(user or "—"))

            color = None
            if selected_id == hid:
                color = Qt.yellow

            if color:
                for col in range(6):
                    self.history_table.item(row_i, col).setBackground(color)

    # ================= OPEN VERSION =================
    def open_version(self, row, col):
        history_id = int(self.history_table.item(row, 0).text())

        # версия из истории
        history_article = get_history_by_id(history_id)
        self.selected_history_id = history_id
        if not history_article:
            return

        # достаём article_id (мы его сохранили через Qt.UserRole)
        item = self.history_table.item(row, 0)
        article_id = item.data(Qt.UserRole)

        from db import get_article_by_id

        # текущая версия статьи
        current_article = get_article_by_id(article_id)
        if not current_article:
            return

        # ⚠️ ВАЖНО: проверь названия полей!
        old_text = current_article.get("content", "")
        new_text = history_article.get("content", "")

        # делаем diff
        diff_html = make_diff_html(old_text, new_text)

        # показываем HTML
        from PyQt5.QtWidgets import QTextEdit

        self.viewer = QTextEdit()
        self.viewer.setWindowTitle("Сравнение версий")
        self.viewer.setReadOnly(True)
        self.viewer.setHtml(diff_html)
        self.viewer.resize(1000, 700)
        self.viewer.show()

    def open_article_preview(self, row, col):
        if row < 0:
            return

        article_id = int(self.article_table.item(row, 0).text())

        from db import get_article_by_id
        article = get_article_by_id(article_id)

        if not article:
            QMessageBox.warning(self, "Ошибка", "Статья не найдена")
            return

        from main_window import ArticleWindow
        self.viewer = ArticleWindow(article)
        self.viewer.show()

    # ================= APPROVE =================
    def approve_article(self):
        self.data_changed.emit()
        row = self.history_table.currentRow()

        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выбери версию")
            return

        item = self.history_table.item(row, 0)
        history_id = int(item.text())

        confirm = QMessageBox.question(
            self,
            "Подтверждение",
            "Применить эту версию?"
        )

        if confirm != QMessageBox.Yes:
            return

        from db import approve_article_version

        approve_article_version(history_id, getattr(self, "user_id", None))

        QMessageBox.information(self, "OK", "Статья обновлена")

        # 🔥 правильное обновление UI
        if self.showing_pending:
            self.load_pending_articles()
        else:
            self.load_articles()

        current_article_row = self.article_table.currentRow()
        if current_article_row >= 0:
            self.load_history(current_article_row, 0)

    # ================= REJECT =================
    def reject_article(self):
        row = self.history_table.currentRow()

        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выбери версию")
            return

        history_id = int(self.history_table.item(row, 0).text())

        from db import update_article_status
        update_article_status(history_id, "rejected")

        QMessageBox.information(self, "OK", "Версия отклонена")

        current_article_row = self.article_table.currentRow()
        if current_article_row >= 0:
            self.load_history(current_article_row, 0)

    # ================= DELETE =================
    def delete_article_ui(self):
        row = self.article_table.currentRow()

        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выбери статью")
            return

        article_id = int(self.article_table.item(row, 0).text())
        title = self.article_table.item(row, 1).text()

        confirm = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Удалить статью:\n{title} ?"
        )

        if confirm != QMessageBox.Yes:
            return

        from db import soft_delete_article
        user_id = getattr(self, "user_id", None)

        soft_delete_article(article_id, user_id)

        QMessageBox.information(self, "OK", "Статья удалена")
        self.load_articles()
        self.history_table.setRowCount(0)

    # ================= ROLLBACK =================
    def rollback_version(self):
        row = self.history_table.currentRow()

        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выбери версию")
            return

        history_id = int(self.history_table.item(row, 0).text())

        confirm = QMessageBox.question(
            self,
            "Подтверждение",
            "Сделать эту версию текущей?"
        )

        if confirm != QMessageBox.Yes:
            return

        from db import rollback_article
        user_id = getattr(self, "user_id", None)

        rollback_article(history_id, user_id)

        QMessageBox.information(self, "OK", "Версия восстановлена")

        current_article_row = self.article_table.currentRow()
        if current_article_row >= 0:
            self.load_history(current_article_row, 0)

    # ================= PENDING =================
    def load_pending_articles(self):
        from db import get_pending_articles

        self.showing_pending = True

        articles = get_pending_articles()
        self.article_table.setRowCount(len(articles))

        for row, (id_, title, views, status) in enumerate(articles):
            self.article_table.setItem(row, 0, QTableWidgetItem(str(id_)))
            self.article_table.setItem(row, 1, QTableWidgetItem(title))
            self.article_table.setItem(row, 2, QTableWidgetItem(str(views)))
            self.article_table.setItem(row, 3, QTableWidgetItem(status))

            for col in range(4):
                self.article_table.item(row, col).setBackground(Qt.yellow)

def closeEvent(self, event):
    print("ADMIN CLOSED")  # 👈 проверка
    if self.on_close:
        self.on_close()
    super().closeEvent(event)
# ================= DIFF =================
def make_diff_html(old_text, new_text):
    import difflib
    import html

    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    opcodes = matcher.get_opcodes()

    result = []

    style = """
    <style>
        body { font-family: Consolas, monospace; background: #fff; }
        table { width: 100%; border-collapse: collapse; }
        td { vertical-align: top; white-space: pre; padding: 2px 8px; }
        .left { width: 50%; border-right: 1px solid #ddd; }
        .right { width: 50%; }
        .add { background: #e6ffed; color: #1a7f37; }
        .del { background: #ffeef0; color: #cf222e; }
        .same { background: #ffffff; }
        .empty { background: #f6f8fa; }
    </style>
    """

    result.append(style)

    result.append("""
    <div style="padding:5px; font-size:12px;">
        <span style="background:#e6ffed; padding:2px 6px;">Добавлено</span>
        <span style="background:#ffeef0; padding:2px 6px; margin-left:10px;">Удалено</span>
    </div>
    """)

    result.append("<table>")

    for tag, i1, i2, j1, j2 in opcodes:

        left_chunk = old_lines[i1:i2]
        right_chunk = new_lines[j1:j2]

        # 🔥 ВАЖНО: если replace и одинаковая длина → сравниваем построчно
        if tag == "replace" and len(left_chunk) == len(right_chunk):
            for l, r in zip(left_chunk, right_chunk):
                similarity = difflib.SequenceMatcher(None, l, r).ratio()

                if similarity > 0.6:
                    # считаем это "изменённой строкой"
                    result.append(f"""
                    <tr>
                        <td class="left del">{html.escape(l)}</td>
                        <td class="right add">{html.escape(r)}</td>
                    </tr>
                    """)
                else:
                    # совсем разные
                    result.append(f"""
                    <tr>
                        <td class="left del">{html.escape(l)}</td>
                        <td class="right empty"></td>
                    </tr>
                    """)
                    result.append(f"""
                    <tr>
                        <td class="left empty"></td>
                        <td class="right add">{html.escape(r)}</td>
                    </tr>
                    """)
            continue

        max_len = max(len(left_chunk), len(right_chunk))

        for i in range(max_len):
            left = html.escape(left_chunk[i]) if i < len(left_chunk) else ""
            right = html.escape(right_chunk[i]) if i < len(right_chunk) else ""

            if tag == "equal":
                l_class = r_class = "same"
            elif tag == "delete":
                l_class = "del"
                r_class = "empty"
            elif tag == "insert":
                l_class = "empty"
                r_class = "add"
            else:
                l_class = "del"
                r_class = "add"

            result.append(f"""
            <tr>
                <td class="left {l_class}">{left}</td>
                <td class="right {r_class}">{right}</td>
            </tr>
            """)

    result.append("</table>")

    return "".join(result)


