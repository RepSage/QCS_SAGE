# QCS_Theme: shared visual theme for the QCS interfaces
# (QCS_Main and QCS_DatabaseView). Centralizes Windows DPI correction,
# the Sun Valley theme (sv-ttk, Windows 11 look) with fallback to the previous
# clam look, the default fonts, the tooltip and window utilities.
# This module does NOT change any qualification logic - only appearance.
#
# Optional dependency: sv-ttk (pip install sv-ttk). Without it, the interface
# keeps working with the old look.

import os
import sys
import traceback
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

try:
    import sv_ttk
except ImportError:
    sv_ttk = None

FONT_FAMILY = 'Segoe UI'
FONT_NORMAL = (FONT_FAMILY, 10)
FONT_BOLD = (FONT_FAMILY, 10, 'bold')
FONT_SMALL = (FONT_FAMILY, 9)
FONT_SMALL_BOLD = (FONT_FAMILY, 9, 'bold')
FONT_TITLE = (FONT_FAMILY, 16, 'bold')
FONT_MONO = ('Consolas', 9)

# Sun Valley surface colors (used in pure tk widgets, e.g. Canvas)
_SURFACE = {'light': '#fafafa', 'dark': '#1c1c1c'}
_SUBTITLE_FG = {'light': '#5f6368', 'dark': '#9aa0a6'}

_current_theme = 'light'


def enable_high_dpi():
    """Makes the process DPI-aware (sharp text on scaled displays).
    Must be called BEFORE creating the Tk() window."""
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def ui_scale(window):
    """Screen scaling factor (1.0 = 96 dpi / 100%)."""
    try:
        return max(window.winfo_fpixels('1i') / 96.0, 1.0)
    except Exception:
        return 1.0


def set_scaled_geometry(window, width, height, min_width=None, min_height=None):
    """Applies geometry in logical pixels, corrected by the screen scaling."""
    s = ui_scale(window)
    window.geometry('%dx%d' % (int(width * s), int(height * s)))
    if min_width and min_height:
        window.minsize(int(min_width * s), int(min_height * s))


def current_theme():
    return _current_theme


def surface_color():
    """Background color of the current theme, for pure tk widgets (Canvas etc.)."""
    return _SURFACE.get(_current_theme, '#fafafa')


def apply_theme(window, theme=None):
    """Applies the visual theme to the window (Tk root). Returns the ttk.Style."""
    global _current_theme
    if theme in ('light', 'dark'):
        _current_theme = theme

    _set_default_fonts(window)
    style = ttk.Style(window)

    if sv_ttk is not None:
        sv_ttk.set_theme(_current_theme, window)
    else:
        _apply_legacy_style(style)

    # QCS's own styles, on top of the base theme
    style.configure('Header.TLabel', font=FONT_BOLD)
    style.configure('Title.TLabel', font=FONT_TITLE)
    style.configure('Subtitle.TLabel', font=FONT_NORMAL,
                    foreground=_SUBTITLE_FG.get(_current_theme, '#5f6368'))
    style.configure('Small.TLabel', font=FONT_SMALL,
                    foreground=_SUBTITLE_FG.get(_current_theme, '#5f6368'))

    # the root window background is not covered by the ttk theme
    try:
        window.configure(bg=surface_color())
    except Exception:
        pass
    return style


def _set_default_fonts(window):
    for name in ('TkDefaultFont', 'TkTextFont', 'TkMenuFont',
                 'TkHeadingFont', 'TkTooltipFont'):
        try:
            tkfont.nametofont(name, window).configure(family=FONT_FAMILY, size=10)
        except Exception:
            pass


def _apply_legacy_style(style):
    """Fallback without sv-ttk: reproduces the clam look used up to v3.2.x."""
    style.theme_use('clam')
    style.configure('TFrame', background='#f0f0f0')
    style.configure('TLabel', background='#f0f0f0', font=FONT_NORMAL)
    style.configure('TLabelframe', background='#f0f0f0')
    style.configure('TLabelframe.Label', background='#f0f0f0')
    style.configure('TButton', padding=5)
    style.configure('TEntry', fieldbackground='white')
    style.configure('TCombobox', fieldbackground='white')
    style.map('TCombobox',
              fieldbackground=[('readonly', 'white')],
              foreground=[('readonly', 'black')])
    style.configure('Accent.TButton', foreground='white', background='#4a90e2',
                    font=FONT_BOLD)
    style.map('Accent.TButton', background=[('active', '#3a7bc8')])


def build_header(parent, title, subtitle, dark_var=None, on_toggle=None,
                 help_command=None):
    """Standard window header: title + subtitle and, optionally,
    the dark mode switch (dark_var/on_toggle) and a help button."""
    header = ttk.Frame(parent)
    text_frame = ttk.Frame(header)
    text_frame.pack(side='left', anchor='w')
    ttk.Label(text_frame, text=title, style='Title.TLabel').pack(anchor='w')
    ttk.Label(text_frame, text=subtitle, style='Subtitle.TLabel').pack(anchor='w')
    if dark_var is not None:
        switch = ttk.Checkbutton(header, text='Dark mode', variable=dark_var,
                                 command=on_toggle)
        if sv_ttk is not None:
            switch.configure(style='Switch.TCheckbutton')
        switch.pack(side='right', anchor='ne', pady=4)
    if help_command is not None:
        ttk.Button(header, text='Help', width=7, command=help_command).pack(
            side='right', anchor='ne', padx=(0, 12))
    return header


def enable_mousewheel(canvas):
    """Mouse-wheel scrolling while the cursor is over the canvas.
    Only scrolls when the content exceeds the visible area: if everything fits,
    the wheel is ignored (avoids the 'empty space' created by scrolling content
    that already fits)."""
    def _on_wheel(event):
        bbox = canvas.bbox('all')
        if bbox is None:
            return
        content_height = bbox[3] - bbox[1]
        if content_height <= canvas.winfo_height():
            return  # everything fits in the window: nothing to scroll
        canvas.yview_scroll(int(-event.delta / 120), 'units')
    canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', _on_wheel))
    canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))


def suppress_notebook_focus_ring(notebook):
    """Removes the dashed focus rectangle that ttk draws on the selected tab's
    label: moves keyboard focus to the tab's content (a Frame does not draw a
    focus ring). Theme-independent (sv-ttk or clam)."""
    def _focus_tab_content(*_):
        try:
            notebook.nametowidget(notebook.select()).focus_set()
        except Exception:
            pass
    notebook.bind('<<NotebookTabChanged>>', _focus_tab_content)
    notebook.after_idle(_focus_tab_content)


class LogConsole:
    """Log panel with a console look and colors by severity, shared by
    QCS_Main and QCS_DatabaseView. The caller positions `self.frame`
    (pack or grid)."""

    def __init__(self, parent, title=' Execution log ', height=8):
        self.frame = ttk.LabelFrame(parent, text=title, padding=10)

        text_frame = ttk.Frame(self.frame)
        text_frame.pack(fill='both', expand=True)
        self._text_frame = text_frame

        self.text = tk.Text(text_frame, height=height, wrap='word', state='disabled',
                            bg='#1e1e1e', fg='#d4d4d4', font=FONT_MONO,
                            relief='flat', borderwidth=0, padx=8, pady=6,
                            insertbackground='#d4d4d4')
        self.text.pack(side='left', fill='both', expand=True)

        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.text.yview)
        scrollbar.pack(side='right', fill='y')
        self.text.config(yscrollcommand=scrollbar.set)

        self.text.tag_configure('error', foreground='#f48771')
        self.text.tag_configure('warning', foreground='#dcdcaa')
        self.text.tag_configure('success', foreground='#89d185')

        self.clear_button = ttk.Button(self.frame, text='Clear log', command=self.clear)
        self.clear_button.pack(side='right', padx=5, pady=(6, 0))

        # Hide log collapses the text area so the content above gains its
        # vertical space (small screens); messages keep accumulating while
        # hidden and reappear on Show log. Packed after clear_button with
        # side='right', so it sits to its LEFT.
        self.hide_button = ttk.Button(self.frame, text='Hide log',
                                      command=self.toggle_visibility)
        self.hide_button.pack(side='right', padx=5, pady=(6, 0))
        self._text_visible = True
        self.on_visibility_change = None   # optional callback(visible: bool)

        ToolTip(self.clear_button, "Erases the messages shown so far")
        ToolTip(self.hide_button, "Collapses the log to free vertical space\n"
                                  "Messages keep accumulating while hidden")

    def _tag_for(self, message):
        # Severity is read from the message's leading label (case-insensitive), so
        # the whole app shares ONE color scheme regardless of the caller. Standard
        # prefixes: 'Info:' (default), 'Warning:' (yellow), 'Error:'/'Critical
        # error:' (red), 'Done:' (green).
        head = message.lstrip().lower()
        if head.startswith(('error', 'critical')):
            return 'error'
        if head.startswith('warning'):
            return 'warning'
        if head.startswith(('done', 'success')):
            return 'success'
        return None

    def log(self, message):
        self.text.config(state='normal')
        self.text.insert('end', message + '\n', self._tag_for(message))
        self.text.see('end')
        self.text.config(state='disabled')

    def clear(self):
        self.text.config(state='normal')
        self.text.delete('1.0', 'end')
        self.text.config(state='disabled')

    def set_visible(self, visible):
        """Shows/hides the text area (the frame with the title and the
        buttons always stays). log() keeps working while hidden."""
        if bool(visible) == self._text_visible:
            return
        if visible:
            # before= keeps the text ABOVE the button row (a plain pack()
            # here would re-add it below, after the buttons)
            self._text_frame.pack(fill='both', expand=True,
                                  before=self.clear_button)
        else:
            self._text_frame.pack_forget()
        self._text_visible = bool(visible)
        self.hide_button.config(text='Hide log' if visible else 'Show log')
        if self.on_visibility_change is not None:
            self.on_visibility_change(self._text_visible)

    def toggle_visibility(self):
        self.set_visible(not self._text_visible)


class ToolTip:
    """Windows 11-style tooltip: dark background, with a display delay."""

    def __init__(self, widget, text, delay=400):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip = None
        self._after_id = None
        self.widget.bind('<Enter>', self._schedule, add='+')
        self.widget.bind('<Leave>', self.hide, add='+')
        self.widget.bind('<ButtonPress>', self.hide, add='+')

    def _schedule(self, event=None):
        self._cancel()
        self._after_id = self.widget.after(self.delay, self.show)

    def _cancel(self):
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def show(self, event=None):
        if self.tooltip is not None:
            return
        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry('+%d+%d' % (x, y))
        try:
            self.tooltip.wm_attributes('-topmost', True)
        except Exception:
            pass
        label = tk.Label(self.tooltip, text=self.text, justify='left',
                         background='#202020', foreground='#f5f5f5',
                         relief='flat', borderwidth=0,
                         font=FONT_SMALL, padx=10, pady=6)
        label.pack()

    def hide(self, event=None):
        self._cancel()
        if self.tooltip is not None:
            self.tooltip.destroy()
            self.tooltip = None


class StreamToLog:
    """File-like object that redirects stdout/stderr to the in-app Log, so the
    program can run with NO console window. Text is buffered until a sink (the
    Log panel's .log method) is attached with set_sink(); complete lines are
    then forwarded. Keeps the full history for the crash dump."""

    encoding = 'utf-8'  # some libraries read sys.stdout.encoding

    def __init__(self):
        self._buffer = ''
        self._pending = []
        self._sink = None
        self.history = []

    def set_sink(self, sink):
        self._sink = sink
        pending, self._pending = self._pending, []
        for line in pending:
            self._safe(line)

    def _safe(self, line):
        try:
            self._sink(line)
        except Exception:
            pass  # the log widget may not exist yet or may be destroyed

    def write(self, text):
        if not text:
            return
        self._buffer += text
        while '\n' in self._buffer:
            line, self._buffer = self._buffer.split('\n', 1)
            self.history.append(line)
            if self._sink is not None:
                self._safe(line)
            else:
                self._pending.append(line)

    def flush(self):
        pass

    def isatty(self):
        return False


_redirect_stream = None

def install_output_redirect():
    """Redirect stdout/stderr to an in-app Log stream (no console needed).
    Returns the StreamToLog; attach the panel with stream.set_sink(log.log)
    once it exists. Early prints are buffered and flushed on attach.

    Idempotent: repeated calls return the SAME stream, so the unified app
    (which imports both tool modules) keeps a single redirect and one shared
    log sink instead of two competing ones."""
    global _redirect_stream
    if _redirect_stream is None:
        _redirect_stream = StreamToLog()
        sys.stdout = _redirect_stream
        sys.stderr = _redirect_stream
    return _redirect_stream


def writable_app_dir():
    """The folder where the app may WRITE its per-user files (settings, crash
    log). Running from source, that is the script folder - unchanged. Frozen,
    it is the folder beside the exe WHEN WRITABLE (per-user installs, the
    portable unzip), else %APPDATA%\\QCS - which is what makes an install into
    Program Files workable (v11.2): that folder is read-only for a regular
    user, and os.access lies about it on Windows, so the probe is a real write.
    """
    if not getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(__file__))
    base = os.path.dirname(sys.executable)
    try:
        probe = os.path.join(base, '.qcs_write_probe')
        with open(probe, 'w') as f:
            f.write('x')
        os.remove(probe)
        return base
    except OSError:
        appdata = os.path.join(os.environ.get('APPDATA', base), 'QCS')
        os.makedirs(appdata, exist_ok=True)
        return appdata


def install_crash_handler(app_name, out_stream=None, base_dir=None):
    """Global excepthook: on an uncaught error (e.g. a crash before the window
    exists, when there is no console to read), write a QCS_crash.log next to the
    program and show a message box, so the failure is never silent."""
    base = base_dir or os.path.dirname(os.path.abspath(__file__))

    def _hook(exc_type, exc, tb):
        report = ''.join(traceback.format_exception(exc_type, exc, tb))
        path = os.path.join(base, 'QCS_crash.log')
        try:
            with open(path, 'w', encoding='utf-8') as f:
                if out_stream is not None and out_stream.history:
                    f.write('\n'.join(out_stream.history) + '\n\n')
                f.write(report)
        except Exception:
            path = '(could not write the crash log)'
        try:
            from tkinter import messagebox
            messagebox.showerror('%s - fatal error' % app_name,
                                 '%s\n\nA crash log was written to:\n%s' % (exc, path))
        except Exception:
            pass

    sys.excepthook = _hook


_icon_photo_ref = None  # keep the iconphoto PhotoImage alive (else the GC drops it)

def set_window_icon(window, icon_name='qcs_icon.ico', app_id='sage.qcs.qualitycontrolsystem'):
    """Use a custom taskbar/window icon. Sets an explicit Windows AppUserModelID
    (so the app shows its OWN icon on the taskbar instead of the interpreter's,
    e.g. Spyder's), then applies the icon. All best-effort: a no-op where
    unavailable or missing.

    Taskbar crispness: Tk's iconbitmap(.ico) often renders blurry on the taskbar
    (it picks a small frame and upscales). Applying a high-res PNG via iconphoto
    LAST gives Windows a 256px image to scale down cleanly."""
    global _icon_photo_ref
    try:
        from ctypes import windll
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass
    base = os.path.dirname(os.path.abspath(__file__))
    # 1) .ico first (title-bar icon, has the small crisp frames)
    try:
        ico = os.path.join(base, icon_name)
        if os.path.isfile(ico):
            window.iconbitmap(ico)
    except Exception:
        pass
    # 2) high-res PNG via iconphoto LAST -> crisp taskbar icon (Tk 8.6 reads PNG)
    try:
        import tkinter as tk
        png = os.path.join(base, os.path.splitext(icon_name)[0] + '.png')
        if os.path.isfile(png):
            if _icon_photo_ref is None:
                _icon_photo_ref = tk.PhotoImage(master=window, file=png)
            window.iconphoto(True, _icon_photo_ref)
    except Exception:
        pass


# Buttons drawn INSIDE a figure (the manual point-cut panels, the light-window
# review). matplotlib's own Button is a flat 0.85 grey box that turns 0.95 on
# hover, with no border - visibly rawer than every other button in the program,
# which is the platform's own (owner, v13.0: the review panels should match the
# Previous / Next row of the panel browser). These are the Fusion/Windows
# push-button colours; a figure in this program is always drawn light, so one
# palette answers for both themes.
PLOT_BUTTON_FACE = '#f0f0f0'
PLOT_BUTTON_HOVER = '#e3effb'
PLOT_BUTTON_EDGE = '#adadad'
PLOT_BUTTON_TEXT = '#1a1a1a'


def style_plot_buttons(buttons, fontsize=9):
    """Gives matplotlib Button widgets the program's button look. Best-effort:
    a styling failure must never cost the operator the review itself."""
    for button in buttons or []:
        try:
            button.color = PLOT_BUTTON_FACE
            button.hovercolor = PLOT_BUTTON_HOVER
            button.ax.set_facecolor(PLOT_BUTTON_FACE)
            for spine in button.ax.spines.values():
                spine.set_visible(True)
                spine.set_color(PLOT_BUTTON_EDGE)
                spine.set_linewidth(1.0)
            button.label.set_fontsize(fontsize)
            button.label.set_color(PLOT_BUTTON_TEXT)
        except Exception:
            pass


def style_plot_window(fig, title=None):
    """Give a matplotlib figure window the app icon and a meaningful title (so it
    matches the rest of the software instead of showing the default matplotlib
    icon and 'Figure N'), and bring it IN FRONT of the main window (a brief
    topmost pulse - not permanently topmost, so other applications can still
    cover it). Best-effort and backend-dependent."""
    try:
        mgr = fig.canvas.manager
        if title:
            mgr.set_window_title(title)
        win = getattr(mgr, 'window', None)
        if win is not None:
            set_window_icon(win)
            try:
                win.lift()
                win.attributes('-topmost', True)
                win.after(300, lambda: win.attributes('-topmost', False))
            except Exception:
                pass
    except Exception:
        pass
