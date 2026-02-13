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
from views.log_viewer_dialog import LogViewerDialog


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

        # Settings menu actions
        self.action_set_working_dir = QAction("Set Working Directory...", self)
        self.action_set_working_dir.setStatusTip("Set working directory for analysis results")
        self.action_set_working_dir.triggered.connect(self._on_set_working_dir)

        self.action_set_source_dir = QAction("Set Source Directory...", self)
        self.action_set_source_dir.setStatusTip("Set source directory for raw images")
        self.action_set_source_dir.triggered.connect(self._on_set_source_dir)

        self.action_view_settings = QAction("View Settings", self)
        self.action_view_settings.setStatusTip("View current settings")
        self.action_view_settings.triggered.connect(self._on_view_settings)

        # Logging actions
        self.action_enable_logging = QAction("Enable Debug Logging", self)
        self.action_enable_logging.setCheckable(True)
        self.action_enable_logging.setChecked(True)  # Enabled by default
        self.action_enable_logging.setStatusTip("Enable or disable debug logging")
        self.action_enable_logging.triggered.connect(self._on_toggle_logging)

        self.action_view_log = QAction("Debug Log", self)
        self.action_view_log.setStatusTip("View debug log")
        self.action_view_log.triggered.connect(self._on_view_log)

        # Analysis menu actions
        self.action_run_analysis = QAction("Run Analysis...", self)
        self.action_run_analysis.setStatusTip("Analyze raw images and generate aggregate CSV")
        self.action_run_analysis.triggered.connect(self._on_run_analysis)

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

        # Analysis menu
        analysis_menu = menubar.addMenu("Analysis")
        analysis_menu.addAction(self.action_run_analysis)

        # Settings menu
        settings_menu = menubar.addMenu("Settings")
        settings_menu.addAction(self.action_set_working_dir)
        settings_menu.addAction(self.action_set_source_dir)
        settings_menu.addSeparator()
        settings_menu.addAction(self.action_enable_logging)
        settings_menu.addAction(self.action_view_log)
        settings_menu.addSeparator()
        settings_menu.addAction(self.action_view_settings)

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
        toolbar.addSeparator()
        toolbar.addAction(self.action_view_log)

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

        # Tab 1: Metadata viewer (with pop-out image button)
        self.image_viewer = ImageViewer()
        self.tab_widget.addTab(self.image_viewer, "Metadata")

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

    def _on_set_working_dir(self) -> None:
        """Handle set working directory action"""
        from utils.config_manager import get_config

        config = get_config()
        current_dir = str(config.get_working_dir())

        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Working Directory",
            current_dir,
            QFileDialog.Option.ShowDirsOnly
        )

        if directory:
            try:
                config.set_working_dir(directory)
                self.status_bar.showMessage(f"Working directory set to: {directory}")
                QMessageBox.information(
                    self,
                    "Working Directory Updated",
                    f"Working directory set to:\n{directory}\n\n"
                    "Analysis results will be saved here."
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to set working directory:\n{str(e)}"
                )

    def _on_set_source_dir(self) -> None:
        """Handle set source directory action"""
        from utils.config_manager import get_config

        config = get_config()
        current_dir = str(config.get_source_dir()) if config.get_source_dir() else ""

        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Source Directory (Raw Images)",
            current_dir,
            QFileDialog.Option.ShowDirsOnly
        )

        if directory:
            try:
                config.set_source_dir(directory)
                # Update data browser source directory
                self.data_browser.source_directory = directory
                self.data_browser.source_path_label.setText(f"📁 {directory}")
                self.data_browser.source_path_label.setStyleSheet("color: black;")

                self.status_bar.showMessage(f"Source directory set to: {directory}")
                QMessageBox.information(
                    self,
                    "Source Directory Updated",
                    f"Source directory set to:\n{directory}\n\n"
                    "Raw images will be loaded from here."
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to set source directory:\n{str(e)}"
                )

    def _on_view_settings(self) -> None:
        """Handle view settings action"""
        from utils.config_manager import get_config

        config = get_config()
        settings = config.get_config_dict()

        message = f"""<h3>Current Settings</h3>
<table>
<tr><td><b>Working Directory:</b></td><td>{settings['working_dir']}</td></tr>
<tr><td><b>Source Directory:</b></td><td>{settings['source_dir'] or 'Not set'}</td></tr>
<tr><td><b>Config File:</b></td><td>{settings['config_path']}</td></tr>
<tr><td><b>Aggregate CSV:</b></td><td>{settings['aggregate_csv']}</td></tr>
</table>"""

        QMessageBox.information(self, "Application Settings", message)

    def _on_run_analysis(self) -> None:
        """Handle run analysis action"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QProgressBar
        from PyQt6.QtCore import QThread, pyqtSignal
        from utils.analysis_runner import AnalysisRunner

        # Create progress dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Running Analysis")
        dialog.setModal(True)
        dialog.resize(600, 400)

        layout = QVBoxLayout()
        dialog.setLayout(layout)

        # Progress text
        progress_text = QTextEdit()
        progress_text.setReadOnly(True)
        layout.addWidget(progress_text)

        # Close button (initially disabled)
        close_button = QPushButton("Close")
        close_button.setEnabled(False)
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

        # Analysis thread
        class AnalysisThread(QThread):
            progress = pyqtSignal(str)
            finished = pyqtSignal(str)
            error = pyqtSignal(str)

            def run(self):
                try:
                    runner = AnalysisRunner()

                    def callback(msg):
                        self.progress.emit(msg)

                    output_path = runner.run_full_analysis(progress_callback=callback)
                    self.finished.emit(str(output_path))
                except Exception as e:
                    self.error.emit(str(e))

        # Create and connect thread
        thread = AnalysisThread()

        def on_progress(msg):
            progress_text.append(msg)

        def on_finished(output_path):
            progress_text.append(f"\n✓ Analysis complete!")
            progress_text.append(f"CSV saved to: {output_path}")
            close_button.setEnabled(True)
            self.status_bar.showMessage(f"Analysis complete: {output_path}")

            # Reload data in browser
            try:
                self.data_browser.reload_data(output_path)
            except Exception:
                pass

        def on_error(error_msg):
            progress_text.append(f"\n✗ Error: {error_msg}")
            close_button.setEnabled(True)

        thread.progress.connect(on_progress)
        thread.finished.connect(on_finished)
        thread.error.connect(on_error)

        # Start analysis
        thread.start()
        dialog.exec()

    def _on_toggle_logging(self, checked: bool) -> None:
        """Handle toggle logging action"""
        from utils.app_logger import get_logger

        logger = get_logger()
        if checked:
            logger.enable()
            self.status_bar.showMessage("Debug logging enabled")
        else:
            logger.disable()
            self.status_bar.showMessage("Debug logging disabled")

    def _on_view_log(self) -> None:
        """Handle view log action"""
        dialog = LogViewerDialog(self)
        dialog.exec()

    def _on_row_selected(self, row_index: int) -> None:
        """Handle row selection in data browser"""
        from utils.app_logger import get_logger
        logger = get_logger()

        try:
            logger.info(f"Row selected: {row_index}")
            row_data = self.data_browser.get_row_data(row_index)

            # Extract file information
            camera = row_data.get('camera', '')
            iso = row_data.get('iso', '')
            exposure_time = row_data.get('exposure_time', '')
            source = row_data.get('source', '')

            logger.debug(f"Row data: camera={camera}, iso={iso}, exposure_time={exposure_time}, source={source}")

            # Try to load image using the file path from data browser
            logger.debug("Getting file path for row")
            file_path = self.data_browser.get_file_path_for_row(row_index)
            logger.debug(f"File path resolved: {file_path}")

            if file_path:
                try:
                    logger.info(f"Loading image: {file_path}")
                    self.image_viewer.load_image(file_path, camera_model=camera)
                    self.tab_widget.setCurrentIndex(0)  # Switch to image viewer tab
                    self.status_bar.showMessage(
                        f"✓ Loaded: {camera} | ISO {iso} | Exp: {exposure_time}s | File: {source}"
                    )
                    logger.info("Image loaded and displayed successfully")
                except Exception as img_error:
                    logger.error(f"Failed to load image: {img_error}", exc_info=True)
                    self.status_bar.showMessage(
                        f"✗ Load failed: {camera} | ISO {iso} | File: {source} | Error: {str(img_error)}"
                    )
            else:
                logger.warning(f"File path not found for row {row_index}, source: {source}")
                self.status_bar.showMessage(
                    f"⚠️ File not found: {camera} | ISO {iso} | File: {source}"
                )

        except Exception as e:
            logger.error(f"Error in row selection: {e}", exc_info=True)
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
