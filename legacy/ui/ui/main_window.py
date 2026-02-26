from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
from ui.sidebar import ModernSidebar

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SoulSync")
        self.setGeometry(100, 100, 800, 600)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout for the central widget
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Add ModernSidebar to the layout
        self.sidebar = ModernSidebar()
        layout.addWidget(self.sidebar)

        # Placeholder for additional components
        # layout.addWidget(OtherComponent())