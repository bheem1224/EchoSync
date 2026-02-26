from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QCheckBox, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView

class DownloadMissingTracksPage(QWidget):
    def __init__(self, tracks, parent=None):
        super().__init__(parent)
        self.tracks = tracks
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        title_label = QLabel("Download Missing Tracks")
        layout.addWidget(title_label)

        self.force_download_checkbox = QCheckBox("Force Download")
        layout.addWidget(self.force_download_checkbox)

        self.organize_checkbox = QCheckBox("Organize by Playlist")
        layout.addWidget(self.organize_checkbox)

        self.analyze_button = QPushButton("Analyze")
        layout.addWidget(self.analyze_button)

        self.track_status_table = QTableWidget()
        self.track_status_table.setColumnCount(4)
        self.track_status_table.setHorizontalHeaderLabels(["Track", "Artist", "Status", "Action"])
        self.track_status_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        for track in self.tracks:
            row_position = self.track_status_table.rowCount()
            self.track_status_table.insertRow(row_position)
            self.track_status_table.setItem(row_position, 0, QTableWidgetItem(track['title']))
            self.track_status_table.setItem(row_position, 1, QTableWidgetItem(track['artist']))
            self.track_status_table.setItem(row_position, 2, QTableWidgetItem("Pending"))
            action_item = QTableWidgetItem("Add to Wishlist")
            self.track_status_table.setItem(row_position, 3, action_item)

        layout.addWidget(self.track_status_table)

        self.setLayout(layout)