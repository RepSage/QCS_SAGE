# QCS_Theme: tema visual compartilhado das interfaces do QCS
# (QCS_Main e QCS_DatabaseView). Centraliza a correcao de DPI do Windows,
# o tema Sun Valley (sv-ttk, visual Windows 11) com fallback para o visual
# clam anterior, as fontes padrao, o tooltip e utilitarios de janela.
# Este modulo NAO altera nenhuma logica de qualificacao - apenas aparencia.
#
# Dependencia opcional: sv-ttk (pip install sv-ttk). Sem ele, a interface
# continua funcionando com o visual antigo.

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

# cores de superficie do Sun Valley (usadas em widgets tk puros, ex.: Canvas)
_SURFACE = {'light': '#fafafa', 'dark': '#1c1c1c'}
_SUBTITLE_FG = {'light': '#5f6368', 'dark': '#9aa0a6'}

_current_theme = 'light'


def enable_high_dpi():
    """Torna o processo ciente de DPI (texto nitido em telas com escala).
    Deve ser chamada ANTES de criar a janela Tk()."""
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def ui_scale(window):
    """Fator de escala da tela (1.0 = 96 dpi / 100%)."""
    try:
        return max(window.winfo_fpixels('1i') / 96.0, 1.0)
    except Exception:
        return 1.0


def set_scaled_geometry(window, width, height, min_width=None, min_height=None):
    """Aplica geometria em pixels logicos, corrigida pela escala da tela."""
    s = ui_scale(window)
    window.geometry('%dx%d' % (int(width * s), int(height * s)))
    if min_width and min_height:
        window.minsize(int(min_width * s), int(min_height * s))


def current_theme():
    return _current_theme


def surface_color():
    """Cor de fundo do tema atual, para widgets tk puros (Canvas etc.)."""
    return _SURFACE.get(_current_theme, '#fafafa')


def apply_theme(window, theme=None):
    """Aplica o tema visual na janela (Tk root). Retorna o ttk.Style."""
    global _current_theme
    if theme in ('light', 'dark'):
        _current_theme = theme

    _set_default_fonts(window)
    style = ttk.Style(window)

    if sv_ttk is not None:
        sv_ttk.set_theme(_current_theme, window)
    else:
        _apply_legacy_style(style)

    # estilos proprios do QCS, por cima do tema base
    style.configure('Header.TLabel', font=FONT_BOLD)
    style.configure('Title.TLabel', font=FONT_TITLE)
    style.configure('Subtitle.TLabel', font=FONT_NORMAL,
                    foreground=_SUBTITLE_FG.get(_current_theme, '#5f6368'))
    style.configure('Small.TLabel', font=FONT_SMALL,
                    foreground=_SUBTITLE_FG.get(_current_theme, '#5f6368'))

    # o fundo da janela raiz nao e coberto pelo tema ttk
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
    """Fallback sem sv-ttk: reproduz o visual clam usado ate a v3.2.x."""
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
    """Cabecalho padrao das janelas: titulo + subtitulo e, opcionalmente,
    o interruptor de modo escuro (dark_var/on_toggle) e um botao de ajuda."""
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
    """Rolagem pela roda do mouse enquanto o cursor esta sobre o canvas.
    So rola quando o conteudo excede a area visivel: se tudo cabe, a roda e
    ignorada (evita o 'espaco vazio' criado ao rolar um conteudo que ja cabe)."""
    def _on_wheel(event):
        bbox = canvas.bbox('all')
        if bbox is None:
            return
        content_height = bbox[3] - bbox[1]
        if content_height <= canvas.winfo_height():
            return  # tudo cabe na janela: nao ha o que rolar
        canvas.yview_scroll(int(-event.delta / 120), 'units')
    canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', _on_wheel))
    canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))


def suppress_notebook_focus_ring(notebook):
    """Remove o retangulo tracejado de foco que o ttk desenha no rotulo da aba
    selecionada: move o foco de teclado para o conteudo da aba (um Frame nao
    desenha anel de foco). Independe do tema (sv-ttk ou clam)."""
    def _focus_tab_content(*_):
        try:
            notebook.nametowidget(notebook.select()).focus_set()
        except Exception:
            pass
    notebook.bind('<<NotebookTabChanged>>', _focus_tab_content)
    notebook.after_idle(_focus_tab_content)


class LogConsole:
    """Painel de log com visual de console e cores por severidade, compartilhado
    pelo QCS_Main e pelo QCS_DatabaseView. O chamador posiciona `self.frame`
    (pack ou grid)."""

    def __init__(self, parent, title=' Execution log ', height=8):
        self.frame = ttk.LabelFrame(parent, text=title, padding=10)

        text_frame = ttk.Frame(self.frame)
        text_frame.pack(fill='both', expand=True)

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

        self.clear_button = ttk.Button(self.frame, text='Clear Log', command=self.clear)
        self.clear_button.pack(side='right', padx=5, pady=(6, 0))

    def _tag_for(self, message):
        if message.startswith(('ERROR', 'CRITICAL')):
            return 'error'
        if message.startswith('WARNING'):
            return 'warning'
        if message.startswith(('SUCCESS', 'Done')):
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


class ToolTip:
    """Tooltip no estilo Windows 11: fundo escuro, com atraso de exibicao."""

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
