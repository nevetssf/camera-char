"""
Plot viewer widget for displaying interactive Plotly charts.
Uses QWebEngineView to embed Plotly HTML plots.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QGroupBox, QMessageBox,
    QDialog, QTableView, QHeaderView
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import pyqtSignal, Qt, QAbstractTableModel, QModelIndex
from typing import Optional, List
import plotly.graph_objects as go
import pandas as pd
from pathlib import Path

from utils.plot_generator import get_plot_generator


class PandasTableModel(QAbstractTableModel):
    """Table model for displaying pandas DataFrame"""

    def __init__(self, data: pd.DataFrame = None):
        super().__init__()
        self._data = data if data is not None else pd.DataFrame()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data.columns)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            value = self._data.iloc[index.row(), index.column()]
            if isinstance(value, float):
                return f"{value:.6f}"
            return str(value)

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._data.columns[section])
            else:
                return str(section + 1)
        return None

    def update_data(self, data: pd.DataFrame):
        """Update the model with new data"""
        self.beginResetModel()
        self._data = data if data is not None else pd.DataFrame()
        self.endResetModel()


class PlotViewer(QWidget):
    """Plot viewer widget with Plotly integration"""

    plot_updated = pyqtSignal()  # Emitted when plot is updated

    def __init__(self, plot_type: str = "ev_vs_iso"):
        """
        Initialize plot viewer.

        Args:
            plot_type: Type of plot (kept for backwards compatibility, now unused)
        """
        super().__init__()

        self.plot_generator = get_plot_generator()
        self.current_figure: Optional[go.Figure] = None
        self.current_data: Optional[pd.DataFrame] = None
        self.data_viewer_dialog: Optional[QDialog] = None

        self._create_ui()
        self._populate_controls()

        # Connect to plot_updated signal to update data viewer
        self.plot_updated.connect(self._update_data_viewer)

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
        from PyQt6.QtWidgets import QCheckBox

        group = QGroupBox("Controls")
        layout = QHBoxLayout()
        group.setLayout(layout)

        # Group selector
        group_label = QLabel("Group:")
        layout.addWidget(group_label)

        self.group_combo = QComboBox()
        self.group_combo.addItem("Camera", "camera")
        self.group_combo.addItem("ISO", "iso")
        self.group_combo.addItem("Exposure Time", "exposure_time")
        self.group_combo.setCurrentIndex(0)  # Default to Camera
        self.group_combo.currentIndexChanged.connect(self._on_control_changed)
        layout.addWidget(self.group_combo)

        layout.addSpacing(20)

        # Y-Axis selector
        yaxis_label = QLabel("Y-Axis:")
        layout.addWidget(yaxis_label)

        self.yaxis_combo = QComboBox()
        self.yaxis_combo.addItem("EV", "ev")
        self.yaxis_combo.addItem("Std Dev", "noise_std")
        self.yaxis_combo.addItem("Mean", "noise_mean")
        self.yaxis_combo.setCurrentIndex(0)  # Default to EV
        self.yaxis_combo.currentIndexChanged.connect(self._on_control_changed)
        layout.addWidget(self.yaxis_combo)

        layout.addSpacing(20)

        # X-Axis selector
        xaxis_label = QLabel("X-Axis:")
        layout.addWidget(xaxis_label)

        self.xaxis_combo = QComboBox()
        self.xaxis_combo.addItem("Exposure Time", "exposure_time")
        self.xaxis_combo.addItem("ISO", "iso")
        self.xaxis_combo.setCurrentIndex(1)  # Default to ISO
        self.xaxis_combo.currentIndexChanged.connect(self._on_control_changed)
        layout.addWidget(self.xaxis_combo)

        layout.addStretch()

        # Log scale checkbox
        self.log_scale_checkbox = QCheckBox("Log Scale X-Axis")
        self.log_scale_checkbox.setChecked(True)  # Default to enabled
        self.log_scale_checkbox.setToolTip("Use logarithmic scale for x-axis")
        self.log_scale_checkbox.stateChanged.connect(self._on_log_scale_changed)
        layout.addWidget(self.log_scale_checkbox)

        # Debug button to show current data
        debug_button = QPushButton("Show Data")
        debug_button.setToolTip("Show the data currently used in the plot")
        debug_button.clicked.connect(self._show_current_data)
        layout.addWidget(debug_button)

        return group

    def _populate_controls(self) -> None:
        """Populate control widgets with data"""
        # No controls to populate - plot type is auto-detected
        pass

    def generate_plot_from_data(self, filtered_data: Optional[pd.DataFrame] = None,
                               group_param: Optional[str] = None,
                               yaxis_param: Optional[str] = None,
                               xaxis_param: Optional[str] = None,
                               group_values: Optional[List] = None,
                               xaxis_values: Optional[List] = None) -> None:
        """
        Generate plot using filtered data from Data Browser.

        Args:
            filtered_data: DataFrame with filtered data from Data Browser (uses all data if None)
            group_param: Parameter to group by (ignored - always uses control value)
            yaxis_param: Parameter for y-axis (ignored - always uses control value)
            xaxis_param: Parameter for x-axis (ignored - always uses control value)
            group_values: Selected values for grouping parameter (None = all values)
            xaxis_values: Selected values for x-axis parameter (None = all values)
        """
        try:
            # If no data provided, use all data
            if filtered_data is None or filtered_data.empty:
                self.status_label.setText("No data to plot")
                return

            # Store the current data for regeneration when controls change
            self.current_data = filtered_data.copy()

            # Always use current control values (ignore passed parameters)
            group_param = self.group_combo.currentData()
            yaxis_param = self.yaxis_combo.currentData()
            xaxis_param = self.xaxis_combo.currentData()

            # Log plot parameters
            from utils.app_logger import get_logger
            logger = get_logger()
            logger.info(f"Plot params: group={group_param}, yaxis={yaxis_param}, xaxis={xaxis_param}")
            logger.info(f"Data columns: {list(filtered_data.columns)}")
            logger.info(f"Data shape: {filtered_data.shape}")
            if xaxis_param in filtered_data.columns:
                logger.info(f"Unique {xaxis_param} values: {filtered_data[xaxis_param].nunique()}")
                logger.info(f"{xaxis_param} values: {sorted(filtered_data[xaxis_param].unique().tolist()[:10])}")  # First 10
            if group_param in filtered_data.columns:
                logger.info(f"Unique {group_param} values: {filtered_data[group_param].nunique()}")
            if yaxis_param in filtered_data.columns:
                logger.info(f"{yaxis_param} range: {filtered_data[yaxis_param].min()} to {filtered_data[yaxis_param].max()}")

            # Update status
            self.status_label.setText("Generating plot...")

            # Filter by x-axis values if specified
            if xaxis_values and len(xaxis_values) > 0 and xaxis_param in filtered_data.columns:
                filtered_data = filtered_data[filtered_data[xaxis_param].isin(xaxis_values)]

            # Get log scale setting from checkbox
            use_log_scale = self.log_scale_checkbox.isChecked()

            # Generate plot with custom grouping and axes
            fig = self._generate_custom_plot(filtered_data, group_param, yaxis_param, xaxis_param, group_values, use_log_scale)

            # Create plot description
            yaxis_label = yaxis_param.replace('_', ' ').title()
            if yaxis_param == 'ev':
                yaxis_label = 'EV'
            elif yaxis_param == 'noise_std':
                yaxis_label = 'Std Dev'
            elif yaxis_param == 'noise_mean':
                yaxis_label = 'Mean'

            plot_description = f"{yaxis_label} vs {xaxis_param.replace('_', ' ').title()} (grouped by {group_param.replace('_', ' ').title()})"

            # Store figure
            self.current_figure = fig

            # Convert to HTML and display with responsive sizing
            # include_plotlyjs=True embeds plotly.js inline for offline support
            html = fig.to_html(
                include_plotlyjs=True,
                config={'responsive': True}
            )
            self.web_view.setHtml(html)

            # Update status
            num_points = len(filtered_data)
            num_groups = filtered_data[group_param].nunique() if group_param in filtered_data.columns else 0
            self.status_label.setText(
                f"{plot_description}: {num_points} data points, {num_groups} groups"
            )

            # Emit signal
            self.plot_updated.emit()

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Plot Generation Failed",
                f"Failed to generate plot:\n{str(e)}"
            )
            self.status_label.setText(f"Error: {str(e)}")

    def _on_log_scale_changed(self) -> None:
        """Handle log scale checkbox state change - regenerate plot"""
        self._on_control_changed()

    def _on_control_changed(self) -> None:
        """Handle control changes - regenerate plot with new settings"""
        # Only regenerate if we have data
        if self.current_data is None or self.current_data.empty:
            return

        # Get selected values from controls
        group_param = self.group_combo.currentData()
        yaxis_param = self.yaxis_combo.currentData()
        xaxis_param = self.xaxis_combo.currentData()

        # Regenerate plot with new settings
        self.generate_plot_from_data(
            filtered_data=self.current_data,
            group_param=group_param,
            yaxis_param=yaxis_param,
            xaxis_param=xaxis_param
        )

    def _show_current_data(self) -> None:
        """Show the current data being used in the plot (non-blocking window)"""
        # Create dialog if it doesn't exist
        if self.data_viewer_dialog is None:
            self.data_viewer_dialog = QDialog(self)
            self.data_viewer_dialog.setWindowTitle("Current Plot Data")
            self.data_viewer_dialog.resize(1000, 600)
            self.data_viewer_dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)

            layout = QVBoxLayout()
            self.data_viewer_dialog.setLayout(layout)

            # Info label
            self.data_info_label = QLabel()
            layout.addWidget(self.data_info_label)

            # Table view
            self.data_table_view = QTableView()
            self.data_table_view.setAlternatingRowColors(True)
            self.data_table_view.setSortingEnabled(True)
            self.data_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            self.data_table_model = PandasTableModel()
            self.data_table_view.setModel(self.data_table_model)
            layout.addWidget(self.data_table_view)

            # Button row
            button_layout = QHBoxLayout()
            layout.addLayout(button_layout)

            export_button = QPushButton("Export CSV...")
            export_button.clicked.connect(self._export_current_data)
            button_layout.addWidget(export_button)

            button_layout.addStretch()

            close_button = QPushButton("Close")
            close_button.clicked.connect(self.data_viewer_dialog.hide)
            button_layout.addWidget(close_button)

        # Show the dialog first (non-blocking), then update data
        # (must be visible before _update_data_viewer, which checks isVisible)
        self.data_viewer_dialog.show()
        self.data_viewer_dialog.raise_()
        self.data_viewer_dialog.activateWindow()

        # Update the data
        self._update_data_viewer()

    def _update_data_viewer(self) -> None:
        """Update the data viewer dialog with current data"""
        # Only update if the dialog exists and is visible
        if self.data_viewer_dialog is None or not self.data_viewer_dialog.isVisible():
            return

        if self.current_data is not None and not self.current_data.empty:
            # Update info label
            info = f"Data Shape: {self.current_data.shape[0]} rows × {self.current_data.shape[1]} columns | "
            info += f"Group: {self.group_combo.currentText()} | "
            info += f"Y-Axis: {self.yaxis_combo.currentText()} | "
            info += f"X-Axis: {self.xaxis_combo.currentText()}"
            self.data_info_label.setText(info)

            # Update table model
            self.data_table_model.update_data(self.current_data)
        else:
            self.data_info_label.setText("No data available")
            self.data_table_model.update_data(pd.DataFrame())

    def _export_current_data(self) -> None:
        """Export current plot data to CSV"""
        from PyQt6.QtWidgets import QFileDialog

        if self.current_data is None or self.current_data.empty:
            QMessageBox.warning(self.data_viewer_dialog, "No Data", "No data to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self.data_viewer_dialog,
            "Export Plot Data",
            "plot_data.csv",
            "CSV Files (*.csv);;All Files (*)"
        )

        if file_path:
            try:
                self.current_data.to_csv(file_path, index=False)
                QMessageBox.information(
                    self.data_viewer_dialog,
                    "Export Successful",
                    f"Exported {len(self.current_data)} rows to:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self.data_viewer_dialog,
                    "Export Failed",
                    f"Failed to export data:\n{str(e)}"
                )

    def _determine_plot_type(self, data: pd.DataFrame) -> str:
        """
        Automatically determine plot type based on filtered data.

        Logic:
        - If ISO is filtered to single value → plot EV vs Time
        - If Exposure Setting/Time is filtered to single value → plot EV vs ISO
        - Otherwise, choose based on which has fewer unique values

        Args:
            data: Filtered DataFrame

        Returns:
            Plot type: "ev_vs_iso" or "ev_vs_time"
        """
        # Count unique values
        unique_isos = data['iso'].nunique() if 'iso' in data.columns else 0
        unique_times = data['exposure_time'].nunique() if 'exposure_time' in data.columns else 0

        # If ISO is filtered to a single value, plot EV vs Time
        if unique_isos == 1:
            return "ev_vs_time"

        # If Exposure Time is filtered to a single value, plot EV vs ISO
        if unique_times == 1:
            return "ev_vs_iso"

        # If both have multiple values, choose based on which has fewer
        # (fewer unique values on one axis means more interesting plot on the other)
        if unique_isos <= unique_times:
            return "ev_vs_time"
        else:
            return "ev_vs_iso"

    def _generate_ev_vs_iso_plot(self, data: pd.DataFrame) -> go.Figure:
        """Generate EV vs ISO plot from filtered data"""
        import plotly.graph_objects as go
        import plotly.colors as pc

        # Ensure required columns exist
        if 'iso' not in data.columns or 'ev' not in data.columns:
            raise ValueError("Data must contain 'iso' and 'ev' columns")

        # Add EV alias if needed
        if 'EV' not in data.columns and 'ev' in data.columns:
            data = data.copy()
            data['EV'] = data['ev']

        # Group by camera
        fig = go.Figure()
        color_sequence = pc.qualitative.Plotly

        cameras = sorted(data['camera'].unique())
        for i, camera in enumerate(cameras):
            camera_data = data[data['camera'] == camera].sort_values('iso')
            color = color_sequence[i % len(color_sequence)]

            # Create custom hover text with formatted values
            hover_text = []
            for _, row in camera_data.iterrows():
                time_val = row.get('exposure_time', row.get('time', 0))
                if time_val > 0:
                    if time_val < 1:
                        shutter_speed = f"1/{round(1/time_val)}s"
                    else:
                        shutter_speed = f"{time_val:.1f}s" if time_val != int(time_val) else f"{int(time_val)}s"
                else:
                    shutter_speed = "N/A"
                hover_text.append(f"{camera}<br>ISO{int(row['iso'])} | {shutter_speed} | {row['EV']:.1f}eV")

            fig.add_trace(go.Scatter(
                x=camera_data['iso'],
                y=camera_data['EV'],
                mode='markers+lines',
                name=camera,
                line=dict(color=color, width=2.5),
                marker=dict(size=8, color=color, line=dict(width=1, color='white')),
                text=hover_text,
                hovertemplate='%{text}<extra></extra>',
            ))

        # Update layout with responsive sizing
        fig.update_xaxes(type='log', title='ISO Sensitivity')
        fig.update_yaxes(title='Exposure Value (EV)')
        fig.update_layout(
            title=dict(text='EV vs ISO', x=0.5, xanchor='center'),
            hovermode="x unified",
            autosize=True,
            font=dict(family="Arial, sans-serif", size=12),
            margin=dict(l=60, r=40, t=60, b=60),
        )

        return fig

    def _generate_ev_vs_time_plot(self, data: pd.DataFrame) -> go.Figure:
        """Generate EV vs Time plot from filtered data"""
        import plotly.graph_objects as go
        import plotly.colors as pc

        # Ensure required columns exist
        if 'exposure_time' not in data.columns or 'ev' not in data.columns:
            raise ValueError("Data must contain 'exposure_time' and 'ev' columns")

        # Add aliases if needed
        if 'EV' not in data.columns and 'ev' in data.columns:
            data = data.copy()
            data['EV'] = data['ev']
        if 'time' not in data.columns and 'exposure_time' in data.columns:
            data['time'] = data['exposure_time']

        # Group by camera
        fig = go.Figure()
        color_sequence = pc.qualitative.Plotly

        cameras = sorted(data['camera'].unique())
        for i, camera in enumerate(cameras):
            camera_data = data[data['camera'] == camera].sort_values('time')
            color = color_sequence[i % len(color_sequence)]

            # Create custom hover text with formatted values
            hover_text = []
            for _, row in camera_data.iterrows():
                time_val = row['time']
                if time_val > 0:
                    if time_val < 1:
                        shutter_speed = f"1/{round(1/time_val)}s"
                    else:
                        shutter_speed = f"{time_val:.1f}s" if time_val != int(time_val) else f"{int(time_val)}s"
                else:
                    shutter_speed = "N/A"
                iso_val = row.get('iso', 'N/A')
                iso_str = f"ISO{int(iso_val)}" if iso_val != 'N/A' else "ISO N/A"
                hover_text.append(f"{camera}<br>{iso_str} | {shutter_speed} | {row['EV']:.1f}eV")

            fig.add_trace(go.Scatter(
                x=camera_data['time'],
                y=camera_data['EV'],
                mode='markers+lines',
                name=camera,
                line=dict(color=color, width=2.5),
                marker=dict(size=8, color=color, line=dict(width=1, color='white')),
                text=hover_text,
                hovertemplate='%{text}<extra></extra>',
            ))

        # Update layout with responsive sizing
        fig.update_xaxes(type='log', title='Exposure Time (seconds)', hoverformat='.6fs')
        fig.update_yaxes(title='Exposure Value (EV)')
        fig.update_layout(
            title=dict(text='EV vs Exposure Time', x=0.5, xanchor='center'),
            hovermode="x unified",
            autosize=True,
            font=dict(family="Arial, sans-serif", size=12),
            margin=dict(l=60, r=40, t=60, b=60),
        )

        return fig

    def _format_exposure_value(self, value: float, is_denominator: bool = False) -> str:
        """
        Format exposure time value as shutter speed string.

        Args:
            value: Exposure time in seconds (or denominator if is_denominator=True)
            is_denominator: If True, value is the denominator of 1/X format (e.g., 60 for 1/60s)
        """
        if pd.isna(value):
            return "N/A"

        if is_denominator:
            # Value is already the denominator (e.g., 60 for 1/60s)
            return f"1/{int(value)}s"
        else:
            # Value is exposure time in seconds
            if value < 1:
                denominator = round(1 / value)
                return f"1/{denominator}s"
            else:
                if value == int(value):
                    return f"{int(value)}s"
                else:
                    return f"{value:.1f}s"

    def _generate_custom_plot(self, data: pd.DataFrame, group_param: str, yaxis_param: str, xaxis_param: str,
                              group_values: Optional[List] = None, use_log_scale: bool = True) -> go.Figure:
        """Generate custom plot with specified grouping, y-axis, and x-axis parameters"""
        import plotly.graph_objects as go
        import plotly.colors as pc

        # Ensure required columns exist
        if xaxis_param not in data.columns or yaxis_param not in data.columns:
            raise ValueError(f"Data must contain '{xaxis_param}' and '{yaxis_param}' columns")

        if group_param not in data.columns:
            raise ValueError(f"Data must contain '{group_param}' column")

        # Work with a copy
        data = data.copy()

        # Filter by group values if specified
        if group_values and len(group_values) > 0:
            data = data[data[group_param].isin(group_values)]

        # Get unique groups and sort them
        groups = sorted(data[group_param].unique())

        # Create figure
        fig = go.Figure()

        # Get color palette
        colors = pc.qualitative.Plotly
        color_idx = 0

        # Plot each group
        for group_value in groups:
            group_data = data[data[group_param] == group_value]

            # Sort by x-axis parameter
            group_data = group_data.sort_values(xaxis_param)

            # Format group value for display (legend and hover text)
            if group_param == 'exposure_time':
                group_label = self._format_exposure_value(group_value, is_denominator=False)
            else:
                group_label = str(group_value)

            # Create hover template
            hover_text = []

            # Build hover text for each point
            for idx, row in group_data.iterrows():
                lines = []

                # Line 1: Camera name or group value
                lines.append(group_label)

                # Line 2: ISO | exposure | EV value (all on one line)
                detail_parts = []

                if 'iso' in row and pd.notna(row['iso']):
                    detail_parts.append(f"ISO{int(row['iso'])}")

                # Add exposure time in shutter speed format
                if xaxis_param == 'exposure_time' or 'exposure_time' in row:
                    time_val = row.get('exposure_time', row.get(xaxis_param, 0))
                    if pd.notna(time_val) and time_val > 0:
                        if time_val < 1:
                            shutter_speed = f"1/{round(1/time_val)}s"
                        else:
                            shutter_speed = f"{time_val:.1f}s" if time_val != int(time_val) else f"{int(time_val)}s"
                        detail_parts.append(shutter_speed)
                elif xaxis_param == 'iso':
                    # For EV vs ISO plots, show exposure time from data
                    if 'exposure_time' in row and pd.notna(row['exposure_time']):
                        time_val = row['exposure_time']
                        if time_val > 0:
                            if time_val < 1:
                                shutter_speed = f"1/{round(1/time_val)}s"
                            else:
                                shutter_speed = f"{time_val:.1f}s" if time_val != int(time_val) else f"{int(time_val)}s"
                            detail_parts.append(shutter_speed)

                # Add y-axis value with appropriate formatting
                y_val = row[yaxis_param]
                if yaxis_param == 'ev':
                    detail_parts.append(f"{y_val:.1f}eV")
                elif yaxis_param == 'noise_std':
                    detail_parts.append(f"Std: {y_val:.2f}")
                elif yaxis_param == 'noise_mean':
                    detail_parts.append(f"Mean: {y_val:.2f}")

                # Join all details on one line
                if detail_parts:
                    lines.append(' | '.join(detail_parts))

                hover_text.append('<br>'.join(lines))

            hovertemplate = '%{text}<extra></extra>'
            custom_data = {'text': hover_text}

            # Create trace for this group
            trace_args = {
                'x': group_data[xaxis_param],
                'y': group_data[yaxis_param],
                'mode': 'lines+markers',
                'name': group_label,
                'marker': dict(size=8),
                'line': dict(color=colors[color_idx % len(colors)], width=2),
                'text': hover_text,
                'hovertemplate': hovertemplate
            }

            fig.add_trace(go.Scatter(**trace_args))

            color_idx += 1

        # Update layout
        xaxis_label = xaxis_param.replace('_', ' ').title()
        if xaxis_param == 'exposure_time':
            xaxis_label = 'Exposure Time (s)'
        elif xaxis_param == 'iso':
            xaxis_label = 'ISO'

        yaxis_label = yaxis_param.replace('_', ' ').title()
        if yaxis_param == 'ev':
            yaxis_label = 'Exposure Value (EV)'
        elif yaxis_param == 'noise_std':
            yaxis_label = 'Noise Standard Deviation'
        elif yaxis_param == 'noise_mean':
            yaxis_label = 'Noise Mean'

        fig.update_layout(
            title=f"{yaxis_label} vs {xaxis_label} (Grouped by {group_param.replace('_', ' ').title()})",
            xaxis_title=xaxis_label,
            yaxis_title=yaxis_label,
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                title=dict(text=group_param.replace('_', ' ').title()),
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02
            ),
            template="plotly_white",
            font=dict(family="Arial, sans-serif", size=12),
            margin=dict(l=60, r=150, t=60, b=60),
        )

        # Use log scale if enabled by checkbox and set hoverformat for time axis
        if use_log_scale:
            if xaxis_param == 'exposure_time':
                fig.update_xaxes(type='log', hoverformat='.6fs')
            else:
                fig.update_xaxes(type='log')
        else:
            if xaxis_param == 'exposure_time':
                fig.update_xaxes(hoverformat='.6fs')

        return fig

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


    def refresh_data(self) -> None:
        """Refresh plot data from generator"""
        self.plot_generator.reload_data()
        self._populate_controls()

    def auto_generate_plot(self, filtered_data: Optional[pd.DataFrame] = None) -> None:
        """
        Automatically generate plot with filtered data.

        Args:
            filtered_data: DataFrame with filtered data from Data Browser
        """
        self.generate_plot_from_data(filtered_data)
