import sys
from PyQt5.QtWidgets import QApplication
from app.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用Fusion风格以获得更现代的外观
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 