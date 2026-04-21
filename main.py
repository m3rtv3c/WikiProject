import sys
from PyQt5.QtWidgets import QApplication
from init_db import init_db, create_default_admin
from main_window import MainWindow

init_db()
create_default_admin()

app = QApplication(sys.argv)
window = MainWindow()
window.show()

sys.exit(app.exec_())