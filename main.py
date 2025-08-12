import sys
from PySide6.QtWidgets import QApplication
from src.views.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Dynamic Scanner")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Scanner Solutions")

    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()