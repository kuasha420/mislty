"""
mislty.gui.tray
~~~~~~~~~~~~~~~

System tray applet (QSystemTrayIcon) with dynamic feline 5-bar RF signal meter,
quick data / mode switcher context actions, desktop notifications, and
minimize-to-tray lifecycle management.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from PySide6.QtCore import QObject, QPoint, QRect, QUrl, Qt, Signal, Slot
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QDesktopServices,
    QGuiApplication,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from mislty.gui.app import MisltyBridge

logger = logging.getLogger("mislty.tray")


def create_feline_signal_icon(bars: int, connected: bool = False, size: int = 32) -> QIcon:
    """
    Render a scalable 5-bar feline RF signal strength icon with real-time
    cellular connection status indicator.
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)

    # Signal bars configuration (5 bars)
    bar_width = max(2, int(size * 0.12))
    gap = max(2, int(size * 0.06))
    max_height = int(size * 0.75)
    start_x = int(size * 0.08)
    baseline_y = int(size * 0.82)

    active_color = QColor("#00f0ff") if connected else QColor("#f39c12")
    inactive_color = QColor("#252b40")

    for i in range(5):
        bar_num = i + 1
        bar_h = int(max_height * (bar_num / 5.0))
        x = start_x + i * (bar_width + gap)
        y = baseline_y - bar_h

        color = active_color if bar_num <= bars else inactive_color
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(x, y, bar_width, bar_h, 1.5, 1.5)

    # Connection Status Dot
    dot_radius = max(2, int(size * 0.08))
    dot_x = size - dot_radius * 2 - 2
    dot_y = size - dot_radius * 2 - 2

    dot_color = QColor("#00e676") if connected else QColor("#ff3366")
    painter.setBrush(QBrush(dot_color))
    painter.setPen(QPen(QColor("#0c0e14"), 1))
    painter.drawEllipse(dot_x, dot_y, dot_radius * 2, dot_radius * 2)

    painter.end()
    return QIcon(pixmap)


class MisltyTray(QObject):
    """
    MisLTy Desktop System Tray Controller.
    """

    def __init__(
        self,
        bridge: MisltyBridge,
        app: Optional[QGuiApplication] = None,
        window: Optional[Any] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.bridge = bridge
        self.app = app or QGuiApplication.instance()
        self.window = window

        self._tray_icon = QSystemTrayIcon(parent=self)
        self._menu = QMenu()

        self._init_menu()
        self._init_connections()
        self.update_icon()

    def _init_menu(self) -> None:
        """Construct tray context menu."""
        # Status header (disabled info display)
        self._status_action = QAction("MisLTy: Disconnected", self)
        self._status_action.setEnabled(False)
        self._menu.addAction(self._status_action)
        self._menu.addSeparator()

        # Connect / Disconnect Toggle
        self._connect_action = QAction("Connect Cellular Data", self)
        self._connect_action.triggered.connect(self._on_toggle_connect)
        self._menu.addAction(self._connect_action)

        # Mode Switch Action
        self._mode_action = QAction("Switch to Pocket Router", self)
        self._mode_action.triggered.connect(self._on_toggle_mode)
        self._menu.addAction(self._mode_action)

        # Web UI Launcher
        self._webui_action = QAction("Open Web Management UI", self)
        self._webui_action.triggered.connect(self._on_open_webui)
        self._menu.addAction(self._webui_action)

        self._menu.addSeparator()

        # Show / Hide Window
        self._toggle_window_action = QAction("Show MisLTy", self)
        self._toggle_window_action.triggered.connect(self.toggle_window)
        self._menu.addAction(self._toggle_window_action)

        # Exit
        self._quit_action = QAction("Quit MisLTy", self)
        self._quit_action.triggered.connect(self._on_quit)
        self._menu.addAction(self._quit_action)

        self._tray_icon.setContextMenu(self._menu)

    def _init_connections(self) -> None:
        """Connect bridge signals to tray updates."""
        self.bridge.connectedChanged.connect(self._on_state_changed)
        self.bridge.signalBarsChanged.connect(self._on_state_changed)
        self.bridge.operatorChanged.connect(self._on_state_changed)
        self.bridge.technologyChanged.connect(self._on_state_changed)
        self.bridge.operationalModeChanged.connect(self._on_mode_changed)
        self.bridge.smsReceived.connect(self._on_sms_received)

        # Left click activation
        self._tray_icon.activated.connect(self._on_tray_activated)

    def show(self) -> None:
        """Display system tray icon."""
        self._tray_icon.show()

    def hide(self) -> None:
        """Hide system tray icon."""
        self._tray_icon.hide()

    @Slot()
    def update_icon(self) -> None:
        """Re-render tray icon with current telemetry."""
        bars = self.bridge.signalBars
        conn = self.bridge.connected
        icon = create_feline_signal_icon(bars=bars, connected=conn)
        self._tray_icon.setIcon(icon)

        # Update Tooltip
        op = self.bridge.operator
        rat = self.bridge.technology
        conn_str = "Connected" if conn else "Disconnected"
        tip = f"MisLTy: {op} ({rat})\nStatus: {conn_str} | Signal: {bars}/5 bars"
        self._tray_icon.setToolTip(tip)

        # Update Menu texts
        if conn:
            self._status_action.setText(f"Connected: {op} ({rat})")
            self._connect_action.setText("Disconnect Cellular Data")
        else:
            self._status_action.setText(f"Ready: {op}")
            self._connect_action.setText("Connect Cellular Data")

    def _on_state_changed(self, *args) -> None:
        """Handle connection/signal changes."""
        self.update_icon()

    def _on_mode_changed(self, mode: str) -> None:
        """Update mode toggle label."""
        if mode == "pocket_router":
            self._mode_action.setText("Switch to USB Modem")
        else:
            self._mode_action.setText("Switch to Pocket Router")

    def _on_sms_received(self, sender: str, body: str) -> None:
        """Show desktop balloon notification on inbound SMS."""
        self._tray_icon.showMessage(
            f"New SMS from {sender}",
            body[:120],
            QSystemTrayIcon.Information,
            4000,
        )

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Toggle main window on tray icon click."""
        if reason == QSystemTrayIcon.Trigger:  # Single left click
            self.toggle_window()

    def toggle_window(self) -> None:
        """Show or hide the main desktop window."""
        if self.window is None:
            return

        if self.window.isVisible():
            self.window.hide()
            self._toggle_window_action.setText("Show MisLTy")
        else:
            self.window.show()
            self.window.raise_()
            self.window.requestActivate()
            self._toggle_window_action.setText("Hide MisLTy")

    def _on_toggle_connect(self) -> None:
        """Toggle cellular data connection."""
        if self.bridge.connected:
            self.bridge.disconnectData()
        else:
            self.bridge.connectData()

    def _on_toggle_mode(self) -> None:
        """Toggle between USB Modem and Pocket Router modes."""
        self.bridge.switchOperationalMode()

    def _on_open_webui(self) -> None:
        """Launch web management UI in default browser."""
        self.bridge.launchWebUi()

    def _on_quit(self) -> None:
        """Gracefully exit application."""
        if self.app:
            self.app.quit()
