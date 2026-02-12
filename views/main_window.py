"""
Main window for Camera Sensor Analyzer application.
Provides the primary UI layout with menu bar, toolbar, and panels.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTabWidget, QMenuBar, QMenu, QToolBar,
    QStatusBar, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence
from typing import Optional

from views.data_browser import DataBrowser
from views.image_viewer import ImageViewer
from views.plot_viewer import PlotViewer
from views.comparison_view import ComparisonView


class MainWindow(QMainWindow):
    """Main application window"""

    # Signals
    file_selected = pyqtSignal(str)  # Emitted when a file is selected

    def __init__(self):
        """Initialize the main window"""
        super().__init__()
        self.setWindowTitle("Camera Sensor Analyzer")
        self.setGeometry(100, 100, 1600, 900)

        # Create UI components
        self._create_actions()
        self._create_menu_bar()
        self._create_toolbar()
        self._create_status_bar()
        self._create_central_widget()

    def _create_actions(self) -> None:
        """Create menu and toolbar actions"""
        # File menu actions
        self.action_open_file = QAction("Open Image...", self)
        self.action_open_file.setShortcut(QKeySequence.StandardKey.Open)
        self.action_open_file.setStatusTip("Open a raw image file")
        self.action_open_file.triggered.connect(self._on_open_file)

        self.action_export_data = QAction("Export Data...", self)
        self.action_export_data.setStatusTip("Export filtered data to CSV")
        self.action_export_data.triggered.connect(self._on_export_data)

        self.action_export_plot = QAction("Export Plot...", self)
        self.action_export_plot.setStatusTip("Export current plot to HTML")
        self.action_export_plot.triggered.connect(self._on_export_plot)

        self.action_quit = QAction("Quit", self)
        self.action_quit.setShortcut(QKeySequence.StandardKey.Quit)
        self.action_quit.setStatusTip("Exit application")
        self.action_quit.triggered.connect(self.close)

        # View menu actions
        self.action_toggle_comparison = QAction("Toggle Comparison View", self)
        self.action_toggle_comparison.setShortcut("Ctrl+Shift+C")
        self.action_toggle_comparison.setCheckable(True)
        self.action_toggle_comparison.setChecked(False)
        self.action_toggle_comparison.setStatusTip("Show/hide comparison view")
        self.action_toggle_comparison.triggered.connect(self._on_toggle_comparison)

        self.action_clear_cache = QAction("Clear Image Cache", self)
        self.action_clear_cache.setStatusTip("Clear cached images to free memory")
        self.action_clear_cache.triggered.connect(self._on_clear_cache)

        # Help menu actions
        self.action_about = QAction("About", self)
        self.action_about.setStatusTip("About Camera Sensor Analyzer")
        self.action_about.triggered.connect(self._on_about)

    def _create_menu_bar(self) -> None:
        """Create the menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")
        file_menu.addAction(self.action_open_file)
        file_menu.addSeparator()
        file_menu.addAction(self.action_export_data)
        file_menu.addAction(self.action_export_plot)
        file_menu.addSeparator()
        file_menu.addAction(self.action_quit)

        # View menu
        view_menu = menubar.addMenu("View")
        view_menu.addAction(self.action_toggle_comparison)
        view_menu.addSeparator()
        view_menu.addAction(self.action_clear_cache)

        # Help menu
        help_menu = menubar.addMenu("Help")
        help_menu.addAction(self.action_about)

    def _create_toolbar(self) -> None:
        """Create the toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        toolbar.addAction(self.action_open_file)
        toolbar.addSeparator()
        toolbar.addAction(self.action_export_data)
        toolbar.addAction(self.action_export_plot)
        toolbar.addSeparator()
        toolbar.addAction(self.action_toggle_comparison)

    def _create_status_bar(self) -> None:
        """Create the status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _create_central_widget(self) -> None:
        """Create the central widget with main layout"""
        # Create main splitter (horizontal)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Data browser (30%)
        self.data_browser = DataBrowser()
        main_splitter.addWidget(self.data_browser)

        # Center panel: Tabbed interface (50%)
        self.tab_widget = QTabWidget()

        # Tab 1: Image viewer
        self.image_viewer = ImageViewer()
        self.tab_widget.addTab(self.image_viewer, "Image Viewer")

        # Tab 2: EV vs ISO plot
        self.plot_ev_iso = PlotViewer(plot_type="ev_vs_iso")
        self.tab_widget.addTab(self.plot_ev_iso, "EV vs ISO")

        # Tab 3: EV vs Time plot
        self.plot_ev_time = PlotViewer(plot_type="ev_vs_time")
        self.tab_widget.addTab(self.plot_ev_time, "EV vs Time")

        main_splitter.addWidget(self.tab_widget)

        # Right panel: Comparison view (20%, initially hidden)
        self.comparison_view = ComparisonView()
        main_splitter.addWidget(self.comparison_view)
        self.comparison_view.setVisible(False)

        # Set splitter proportions (30%, 50%, 20%)
        main_splitter.setStretchFactor(0, 3)  # Data browser
        main_splitter.setStretchFactor(1, 5)  # Tabs
        main_splitter.setStretchFactor(2, 2)  # Comparison

        # Set as central widget
        self.setCentralWidget(main_splitter)

        # Connect signals
        self._connect_signals()

    def _connect_signals(self) -> None:
        """Connect signals between components"""
        # When row is selected in data browser, load image
        self.data_browser.row_selected.connect(self._on_row_selected)

        # When plot viewer camera selection changes, update data browser
        # (This could be implemented for bidirectional filtering)

    def _on_open_file(self) -> None:
        """Handle open file action"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image File",
            "",
            "Image Files (*.dng *.DNG *.erf *.ERF *.tiff *.tif *.TIFF *.TIF);;All Files (*)"
        )

        if file_path:
            self.file_selected.emit(file_path)
            self.image_viewer.load_image(file_path)
            self.status_bar.showMessage(f"Loaded: {file_path}")

    def _on_export_data(self) -> None:
        """Handle export data action"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Data",
            "filtered_data.csv",
            "CSV Files (*.csv);;All Files (*)"
        )

        if file_path:
            try:
                self.data_browser.export_data(file_path)
                self.status_bar.showMessage(f"Data exported to: {file_path}")
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Data exported successfully to:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Failed to export data:\n{str(e)}"
                )

    def _on_export_plot(self) -> None:
        """Handle export plot action"""
        # Get current tab
        current_index = self.tab_widget.currentIndex()

        if current_index == 1:  # EV vs ISO
            plot_viewer = self.plot_ev_iso
        elif current_index == 2:  # EV vs Time
            plot_viewer = self.plot_ev_time
        else:
            QMessageBox.warning(
                self,
                "No Plot Selected",
                "Please select a plot tab (EV vs ISO or EV vs Time) to export."
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Plot",
            "plot.html",
            "HTML Files (*.html);;PNG Images (*.png);;All Files (*)"
        )

        if file_path:
            try:
                plot_viewer.export_plot(file_path)
                self.status_bar.showMessage(f"Plot exported to: {file_path}")
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Plot exported successfully to:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Failed to export plot:\n{str(e)}"
                )

    def _on_toggle_comparison(self, checked: bool) -> None:
        """Handle toggle comparison view action"""
        self.comparison_view.setVisible(checked)

    def _on_clear_cache(self) -> None:
        """Handle clear cache action"""
        self.image_viewer.clear_cache()
        self.status_bar.showMessage("Image cache cleared")

    def _on_about(self) -> None:
        """Handle about action"""
        QMessageBox.about(
            self,
            "About Camera Sensor Analyzer",
            "<h2>Camera Sensor Analyzer</h2>"
            "<p>A desktop application for analyzing camera sensor noise characteristics.</p>"
            "<p>Built with PyQt6 and Plotly</p>"
            "<p>Version 1.0</p>"
        )

    def _on_row_selected(self, row_index: int) -> None:
        """Handle row selection in data browser"""
        try:
            row_data = self.data_browser.get_row_data(row_index)

            # Extract file information
            camera = row_data.get('camera', '')
            iso = row_data.get('iso', '')
            exposure_time = row_data.get('exposure_time', '')

            # Update status bar
            self.status_bar.showMessage(
                f"Selected: {camera} | ISO {iso} | Exp: {exposure_time}s"
            )

            # Try to load image if file path is available
            if 'file_path' in row_data:
                file_path = row_data['file_path']
                self.image_viewer.load_image(file_path, camera_model=camera)
                self.tab_widget.setCurrentIndex(0)  # Switch to image viewer tab

        except Exception as e:
            self.status_bar.showMessage(f"Error: {str(e)}")

    def show_message(self, message: str, timeout: int = 5000) -> None:
        """
        Show a message in the status bar.

        Args:
            message: Message text
            timeout: Timeout in milliseconds
        """
        self.status_bar.showMessage(message, timeout)

    def show_error(self, title: str, message: str) -> None:
        """
        Show an error dialog.

        Args:
            title: Dialog title
            message: Error message
        """
        QMessageBox.critical(self, title, message)

    def show_info(self, title: str, message: str) -> None:
        """
        Show an information dialog.

        Args:
            title: Dialog title
            message: Information message
        """
        QMessageBox.information(self, title, message)
