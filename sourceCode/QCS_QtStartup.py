# -*- coding: utf-8 -*-
"""Single instance and an immediate splash for the Qt shell (v14.1.0).

GitHub issue #49: on a clean install, 'Launch QCS after installation' started
the program and nothing appeared for a long time - the first start of the
frozen bundle loads hundreds of libraries, each scanned by the antivirus, and
QCS_QtApp imports its heavy modules before any window can exist (3.5 s even
warm, from source). The operator started QCS again and got TWO windows.

So, before the heavy imports, the program (QCS_QtApp run as __main__):
  1. takes a per-user lock file; a second start that finds it taken asks the
     running instance - over a local socket - to bring its window to the
     front, and exits;
  2. shows a splash at once, closed when the main window appears.

Only light Qt modules are imported here, on purpose. Nothing in this module
touches the operator's settings.
"""
import ctypes
import os
import re
import sys

from PySide6.QtCore import QDir, QLockFile, QRect, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QSplashScreen

import QCS_QtTheme as qtheme   # splash colours/sizes; light (~0.1 s), no app state

_ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qcs_icon.png')
_ACTIVATE = b'activate\n'


def instance_key():
    """One instance per Windows user (two users on one machine each get theirs).
    QCS_INSTANCE_KEY overrides it - for release smoke tests only, so a test
    copy never talks to the operator's running QCS (a test that used the real
    key brought the operator's window forward and exited, 2026-11-12)."""
    override = os.environ.get('QCS_INSTANCE_KEY')
    if override:
        return re.sub(r'[^A-Za-z0-9_.-]', '_', override)
    user = os.environ.get('USERNAME') or os.environ.get('USER') or 'user'
    return 'QCS-SAGE-%s' % re.sub(r'[^A-Za-z0-9_.-]', '_', user)


class SingleInstance:
    """The first instance owns a lock file and listens on a local socket;
    later ones forward an 'activate' request to it and exit."""

    def __init__(self, key=None, lock_dir=None):
        self.key = key or instance_key()
        self.lock = QLockFile(os.path.join(lock_dir or QDir.tempPath(), self.key + '.lock'))
        # never stale by AGE (a session can last days); a lock left by a
        # crashed process is still removed - QLockFile checks its PID
        self.lock.setStaleLockTime(0)
        self.server = None
        self._callback = None
        self._pending = False

    def acquire(self):
        """True: this is the first instance (it owns the lock and listens).
        False: another instance runs and was asked to come to the front."""
        if self.lock.tryLock(200):
            QLocalServer.removeServer(self.key)       # a crashed run's pipe name
            self.server = QLocalServer()
            self.server.newConnection.connect(self._on_connection)
            self.server.listen(self.key)
            return True
        self.forward()
        return False

    def forward(self, attempts=40):
        """Asks the running instance to show itself. It may still be starting
        (its server listens from the first second, its window comes later),
        so connection attempts are retried for a few seconds."""
        if sys.platform == 'win32':
            # this process is the one the operator just started, so it holds
            # the foreground right and may hand it over (ASFW_ANY)
            try:
                ctypes.windll.user32.AllowSetForegroundWindow(0xFFFFFFFF)
            except (AttributeError, OSError):
                pass
        for _ in range(attempts):
            sock = QLocalSocket()
            sock.connectToServer(self.key)
            if sock.waitForConnected(250):
                sock.write(_ACTIVATE)
                sock.waitForBytesWritten(1000)
                sock.disconnectFromServer()
                return True
        return False

    def on_activate(self, callback):
        """Registers what to do on a second start; replays one that arrived
        while the main window did not exist yet."""
        self._callback = callback
        if self._pending:
            self._pending = False
            callback()

    def _on_connection(self):
        while self.server.hasPendingConnections():
            conn = self.server.nextPendingConnection()
            conn.disconnected.connect(conn.deleteLater)
        if self._callback:
            self._callback()
        else:
            self._pending = True


def splash_pixmap(app):
    """The splash card (owner design, 2026-11-12): the icon in a white border
    and the message in bold on the white band below it, in the system UI font.
    Drawn at the screen's device-pixel ratio so it stays sharp on scaled
    displays. Sizes and colours live in QCS_QtTheme."""
    icon_px, margin, band = qtheme.SPLASH_ICON_PX, qtheme.SPLASH_MARGIN_PX, qtheme.SPLASH_BAND_PX
    width, height = icon_px + 2 * margin, icon_px + margin + band
    screen = app.primaryScreen()
    ratio = screen.devicePixelRatio() if screen else 1.0
    pix = QPixmap(round(width * ratio), round(height * ratio))
    pix.setDevicePixelRatio(ratio)
    pix.fill(QColor(qtheme.SPLASH_CARD))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    icon = QPixmap(_ICON)
    if not icon.isNull():
        painter.drawPixmap(QRect(margin, margin, icon_px, icon_px), icon)
    font = QFont(app.font())                 # the system UI family (Segoe UI)
    font.setPointSize(qtheme.SPLASH_POINT_SIZE)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor(qtheme.SPLASH_TEXT))
    painter.drawText(QRect(0, margin + icon_px, width, band), int(Qt.AlignmentFlag.AlignCenter),
                     qtheme.SPLASH_MESSAGE)
    painter.setPen(QPen(QColor(qtheme.SPLASH_OUTLINE), 1))
    painter.drawRect(0, 0, width - 1, height - 1)
    painter.end()
    return pix


def show_splash(app):
    """A splash on screen at once; the caller closes it with finish(window)."""
    splash = QSplashScreen(splash_pixmap(app))
    splash.show()
    app.processEvents()
    return splash


def bring_to_front(window):
    if window.isMinimized():
        window.showNormal()
    window.show()
    window.raise_()
    window.activateWindow()


def early_startup():
    """(app, instance, splash) for the first instance; exits a later one."""
    app = QApplication.instance() or QApplication(sys.argv)
    instance = SingleInstance()
    if not instance.acquire():
        sys.exit(0)
    return app, instance, show_splash(app)
