import sys
import os
from PyQt5.QtWidgets import QApplication
from init_db import init_db, create_default_admin
from main_window import MainWindow

# Функция для определения пути к ресурсам
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

init_db()
create_default_admin()

app = QApplication(sys.argv)

logo = resource_path("Wikipedia-logo-v2.svg.png")

window = MainWindow()
window.show()

sys.exit(app.exec_())