"""
Plot viewer widget for displaying interactive Plotly charts.
Uses QWebEngineView to embed Plotly HTML plots.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QGroupBox, QListWidget,
    QAbstractItemView, QMessageBox
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from typing import Optional, List
import plotly.graph_objects as go
from pathlib import Path

from utils.plot_generator import get_plot_generator


class PlotViewer(QWidget):
    """Plot viewer widget with Plotly integration"""

    plot_updated = pyqtSignal()  # Emitted when plot is updated

    def __init__(self, plot_type: str = "ev_vs_iso"):
        """
        Initialize plot viewer.

        Args:
            plot_type: Type of plot ("ev_vs_iso" or "ev_vs_time")
        """
        super().__init__()

        self.plot_type = plot_type
        self.plot_generator = get_plot_generator()
        self.current_figure: Optional[go.Figure] = None

        self._create_ui()
        self._populate_controls()

    def _create_ui(self) -> None:
        """Create user interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Controls
        controls_group = self._create_controls()
        layout.addWidget(controls_group)

        # Web view for Plotly
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view, stretch=1)

        # Status label
        self.status_label = QLabel("Select parameters and click 'Generate Plot'")
        layout.addWidget(self.status_label)

    def _create_controls(self) -> QGroupBox:
        """Create control group"""
        group = QGroupBox("Plot Controls")
        layout = QVBoxLayout()
        group.setLayout(layout)

        # Parameter selection (depends on plot type)
        param_layout = QHBoxLayout()

        if self.plot_type == "ev_vs_iso":
            # EV vs ISO: select exposure time
            param_label = QLabel("Exposure Time (s):")
            self.param_combo = QComboBox()
            param_layout.addWidget(param_label)
            param_layout.addWidget(self.param_combo)

        elif self.plot_type == "ev_vs_time":
            # EV vs Time: select ISO
            param_label = QLabel("ISO:")
            self.param_combo = QComboBox()
            param_layout.addWidget(param_label)
            param_layout.addWidget(self.param_combo)

        param_layout.addStretch()
        layout.addLayout(param_layout)

        # Camera selection
        camera_layout = QHBoxLayout()
        camera_label = QLabel("Select Cameras:")
        self.camera_list = QListWidget()
        self.camera_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.camera_list.setMaximumHeight(150)
        camera_layout.addWidget(camera_label)
        camera_layout.addWidget(self.camera_list)
        layout.addLayout(camera_layout)

        # Buttons
        button_layout = QHBoxLayout()

        self.btn_generate = QPushButton("Generate Plot")
        self.btn_generate.clicked.connect(self._on_generate_plot)
        button_layout.addWidget(self.btn_generate)

        self.btn_select_all = QPushButton("Select All Cameras")
        self.btn_select_all.clicked.connect(self._on_select_all_cameras)
        button_layout.addWidget(self.btn_select_all)

        self.btn_clear_selection = QPushButton("Clear Selection")
        self.btn_clear_selection.clicked.connect(self._on_clear_selection)
        button_layout.addWidget(self.btn_clear_selection)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        return group

    def _populate_controls(self) -> None:
        """Populate control widgets with data"""
        # Populate parameter combo
        if self.plot_type == "ev_vs_iso":
            exposure_times = self.plot_generator.get_unique_exposure_times()
            for time in exposure_times:
                self.param_combo.addItem(str(time), time)
        elif self.plot_type == "ev_vs_time":
            isos = self.plot_generator.get_unique_isos()
            for iso in isos:
                self.param_combo.addItem(str(iso), iso)

        # Populate camera list
        cameras = self.plot_generator.get_unique_cameras()
        for camera in cameras:
            self.camera_list.addItem(camera)

        # Select all cameras by default
        self._on_select_all_cameras()

    def _on_generate_plot(self) -> None:
        """Handle generate plot button"""
        try:
            # Get selected parameter
            if self.param_combo.currentIndex() < 0:
                QMessageBox.warning(
                    self,
                    "No Parameter Selected",
                    "Please select a parameter value."
                )
                return

            param_value = self.param_combo.currentData()

            # Get selected cameras
            selected_cameras = [
                item.text() for item in self.camera_list.selectedItems()
            ]

            if not selected_cameras:
                QMessageBox.warning(
                    self,
                    "No Cameras Selected",
                    "Please select at least one camera."
                )
                return

            # Generate plot
            self.status_label.setText("Generating plot...")

            if self.plot_type == "ev_vs_iso":
                fig = self.plot_generator.generate_ev_vs_iso_plot(
                    exposure_time=param_value,
                    camera_filter=selected_cameras
                )
                title = f"EV vs ISO (Exposure Time: {param_value}s)"
            elif self.plot_type == "ev_vs_time":
                fig = self.plot_generator.generate_ev_vs_time_plot(
                    iso=param_value,
                    camera_filter=selected_cameras
                )
                title = f"EV vs Time (ISO: {param_value})"
            else:
                raise ValueError(f"Unknown plot type: {self.plot_type}")

            # Store figure
            self.current_figure = fig

            # Convert to HTML and display
            html = fig.to_html(include_plotlyjs='cdn')
            self.web_view.setHtml(html)

            # Update status
            self.status_label.setText(
                f"Plot generated: {title} | {len(selected_cameras)} cameras"
            )

            # Emit signal
            self.plot_updated.emit()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Plot Generation Failed",
                f"Failed to generate plot:\n{str(e)}"
            )
            self.status_label.setText(f"Error: {str(e)}")

    def _on_select_all_cameras(self) -> None:
        """Select all cameras"""
        self.camera_list.selectAll()

    def _on_clear_selection(self) -> None:
        """Clear camera selection"""
        self.camera_list.clearSelection()

    def export_plot(self, file_path: str) -> None:
        """
        Export current plot to file.

        Args:
            file_path: Output file path
        """
        if self.current_figure is None:
            raise ValueError("No plot to export")

        file_path = Path(file_path)
        suffix = file_path.suffix.lower()

        if suffix == '.html':
            # Export as HTML
            self.plot_generator.export_plot_html(
                self.current_figure,
                str(file_path)
            )
        elif suffix in ['.png', '.jpg', '.jpeg', '.svg', '.pdf']:
            # Export as static image
            self.plot_generator.export_plot_image(
                self.current_figure,
                str(file_path)
            )
        else:
            raise ValueError(f"Unsupported export format: {suffix}")

    def set_camera_filter(self, cameras: List[str]) -> None:
        """
        Set camera filter selection.

        Args:
            cameras: List of camera models to select
        """
        self.camera_list.clearSelection()

        for i in range(self.camera_list.count()):
            item = self.camera_list.item(i)
            if item.text() in cameras:
                item.setSelected(True)

    def set_parameter(self, value: any) -> None:
        """
        Set parameter value.

        Args:
            value: Parameter value to set
        """
        for i in range(self.param_combo.count()):
            if self.param_combo.itemData(i) == value:
                self.param_combo.setCurrentIndex(i)
                return

    def refresh_data(self) -> None:
        """Refresh plot data from generator"""
        self.plot_generator.reload_data()
        self._populate_controls()

    def auto_generate_plot(self) -> None:
        """Automatically generate plot with current selections"""
        if self.param_combo.currentIndex() >= 0:
            self._on_generate_plot()
