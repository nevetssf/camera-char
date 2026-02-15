"""
Plot viewer widget for displaying interactive Plotly charts.
Uses QWebEngineView to embed Plotly HTML plots.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QGroupBox, QMessageBox
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import pyqtSignal
from typing import Optional, List
import plotly.graph_objects as go
import pandas as pd
from pathlib import Path

from utils.plot_generator import get_plot_generator


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
        from PyQt6.QtWidgets import QCheckBox

        group = QGroupBox("Plot")
        layout = QHBoxLayout()
        group.setLayout(layout)

        # Info label showing current plot type
        self.plot_info_label = QLabel("Plot will auto-update based on filters")
        layout.addWidget(self.plot_info_label)

        layout.addStretch()

        # Log scale checkbox
        self.log_scale_checkbox = QCheckBox("Log Scale X-Axis")
        self.log_scale_checkbox.setChecked(True)  # Default to enabled
        self.log_scale_checkbox.setToolTip("Use logarithmic scale for x-axis")
        self.log_scale_checkbox.stateChanged.connect(self._on_log_scale_changed)
        layout.addWidget(self.log_scale_checkbox)

        return group

    def _populate_controls(self) -> None:
        """Populate control widgets with data"""
        # No controls to populate - plot type is auto-detected
        pass

    def generate_plot_from_data(self, filtered_data: Optional[pd.DataFrame] = None,
                               group_param: str = 'camera',
                               xaxis_param: str = 'iso',
                               group_values: Optional[List] = None,
                               xaxis_values: Optional[List] = None) -> None:
        """
        Generate plot using filtered data from Data Browser.

        Args:
            filtered_data: DataFrame with filtered data from Data Browser (uses all data if None)
            group_param: Parameter to group by (e.g., 'camera', 'iso', 'exposure_time')
            xaxis_param: Parameter for x-axis (e.g., 'iso', 'exposure_time')
            group_values: Selected values for grouping parameter (None = all values)
            xaxis_values: Selected values for x-axis parameter (None = all values)
        """
        try:
            # If no data provided, use all data
            if filtered_data is None or filtered_data.empty:
                self.status_label.setText("No data to plot")
                self.plot_info_label.setText("No data available")
                return

            # Update status
            self.status_label.setText("Generating plot...")

            # Filter by x-axis values if specified
            if xaxis_values and len(xaxis_values) > 0 and xaxis_param in filtered_data.columns:
                filtered_data = filtered_data[filtered_data[xaxis_param].isin(xaxis_values)]

            # Get log scale setting from checkbox
            use_log_scale = self.log_scale_checkbox.isChecked()

            # Generate plot with custom grouping and x-axis
            fig = self._generate_custom_plot(filtered_data, group_param, xaxis_param, group_values, use_log_scale)

            # Create plot description
            plot_description = f"EV vs {xaxis_param.replace('_', ' ').title()} (grouped by {group_param.replace('_', ' ').title()})"

            # Store figure
            self.current_figure = fig

            # Convert to HTML and display with responsive sizing
            html = fig.to_html(
                include_plotlyjs='cdn',
                config={'responsive': True}
            )
            self.web_view.setHtml(html)

            # Update status and info
            num_points = len(filtered_data)
            num_groups = filtered_data[group_param].nunique() if group_param in filtered_data.columns else 0
            self.status_label.setText(
                f"{plot_description}: {num_points} data points, {num_groups} groups"
            )
            self.plot_info_label.setText(f"Showing: {plot_description}")

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
            self.plot_info_label.setText("Error generating plot")

    def _on_log_scale_changed(self) -> None:
        """Handle log scale checkbox state change - regenerate plot"""
        # Note: Plot will be regenerated when filters change in the data browser
        # This is just a placeholder for future manual regeneration if needed
        pass

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

            fig.add_trace(go.Scatter(
                x=camera_data['iso'],
                y=camera_data['EV'],
                mode='markers+lines',
                name=camera,
                line=dict(color=color, width=2.5),
                marker=dict(size=8, color=color, line=dict(width=1, color='white')),
                hovertemplate=f'{camera}: %{{y:.2f}} EV<extra></extra>',
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

            fig.add_trace(go.Scatter(
                x=camera_data['time'],
                y=camera_data['EV'],
                mode='markers+lines',
                name=camera,
                line=dict(color=color, width=2.5),
                marker=dict(size=8, color=color, line=dict(width=1, color='white')),
                hovertemplate=f'{camera}: %{{y:.2f}} EV<extra></extra>',
            ))

        # Update layout with responsive sizing
        fig.update_xaxes(type='log', title='Exposure Time (seconds)')
        fig.update_yaxes(title='Exposure Value (EV)')
        fig.update_layout(
            title=dict(text='EV vs Exposure Time', x=0.5, xanchor='center'),
            hovermode="x unified",
            autosize=True,
            font=dict(family="Arial, sans-serif", size=12),
            margin=dict(l=60, r=40, t=60, b=60),
        )

        return fig

    def _generate_custom_plot(self, data: pd.DataFrame, group_param: str, xaxis_param: str,
                              group_values: Optional[List] = None, use_log_scale: bool = True) -> go.Figure:
        """Generate custom plot with specified grouping and x-axis parameters"""
        import plotly.graph_objects as go
        import plotly.colors as pc

        # Ensure required columns exist
        if xaxis_param not in data.columns or 'ev' not in data.columns:
            raise ValueError(f"Data must contain '{xaxis_param}' and 'ev' columns")

        if group_param not in data.columns:
            raise ValueError(f"Data must contain '{group_param}' column")

        # Add EV alias if needed
        if 'EV' not in data.columns and 'ev' in data.columns:
            data = data.copy()
            data['EV'] = data['ev']

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

            # Create hover template
            # If x-axis is exposure_time and exposure_setting exists, show setting in hover
            if xaxis_param == 'exposure_time' and 'exposure_setting' in group_data.columns:
                # Create custom text with exposure settings formatted as fractions
                hover_text = []
                for setting, ev, time_val in zip(group_data['exposure_setting'], group_data['EV'], group_data['exposure_time']):
                    # Format exposure setting as "1/X" fraction
                    if pd.notna(setting) and setting != '':
                        # If setting is already a string like "1/4000", use it
                        if isinstance(setting, str) and '/' in str(setting):
                            formatted_setting = setting
                        else:
                            # Otherwise, calculate from exposure time
                            if time_val > 0:
                                denominator = int(1.0 / time_val)
                                formatted_setting = f"1/{denominator}"
                            else:
                                formatted_setting = str(setting)
                    else:
                        # Fallback: calculate from exposure time
                        if time_val > 0:
                            denominator = int(1.0 / time_val)
                            formatted_setting = f"1/{denominator}"
                        else:
                            formatted_setting = f"{time_val:.4f}s"

                    hover_text.append(f'{group_param}: {group_value}<br>Exposure: {formatted_setting}<br>EV: {ev:.2f}')

                hovertemplate = '%{text}<extra></extra>'
                custom_data = {'text': hover_text}
            else:
                # Standard hover template
                xaxis_display = xaxis_param.replace('_', ' ').title()
                hover_text = None
                hovertemplate = f'{group_param}: {group_value}<br>{xaxis_display}: %{{x}}<br>EV: %{{y:.2f}}<extra></extra>'
                custom_data = {}

            # Create trace for this group
            trace_args = {
                'x': group_data[xaxis_param],
                'y': group_data['EV'],
                'mode': 'lines+markers',
                'name': str(group_value),
                'marker': dict(size=8),
                'line': dict(color=colors[color_idx % len(colors)], width=2),
                'hovertemplate': hovertemplate
            }

            # Add custom hover text if using exposure settings
            if hover_text:
                trace_args['text'] = hover_text
                trace_args['hoverinfo'] = 'text'

            fig.add_trace(go.Scatter(**trace_args))

            color_idx += 1

        # Update layout
        xaxis_label = xaxis_param.replace('_', ' ').title()
        if xaxis_param == 'exposure_time':
            xaxis_label = 'Exposure Time (s)'
        elif xaxis_param == 'iso':
            xaxis_label = 'ISO'

        fig.update_layout(
            title=f"EV vs {xaxis_label} (Grouped by {group_param.replace('_', ' ').title()})",
            xaxis_title=xaxis_label,
            yaxis_title="Exposure Value (EV)",
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

        # Use log scale if enabled by checkbox
        if use_log_scale:
            fig.update_xaxes(type='log')

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
