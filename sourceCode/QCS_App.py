"""QCS unified application.

Single entry point that hosts both tools in one window: a menu bar
(File / Edit / View / Tools / Help) plus a notebook with two tabs,
"Data Qualification" (QCS_Main) and "Data Visualization" (QCS_DatabaseView).
Replaces the two separate .bat launchers.
"""
import os
import webbrowser

import QCS_DataHandler as data
import QCS_Theme as theme

# One shared stdout/stderr redirect for the whole app (idempotent: the two tool
# modules also call it on import, but they all get the SAME stream).
_out = theme.install_output_redirect()

from tkinter import *          # noqa: F401,F403  (project style: Tk, Menu, BooleanVar, ...)
import tkinter as tk
from tkinter import ttk, messagebox

import QCS_Main as qual
import QCS_DatabaseView as viz

# Both tools share ONE preferences dict, so saving from either tab writes the
# same qcs_user_settings.json without clobbering the other tab's keys.
qual.USER_PREFS = viz.USER_PREFS

theme.install_crash_handler('QCS', _out)

MANUAL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           'Quality Control System (SAGE) - User Manual.html')


def open_manual():
    if os.path.isfile(MANUAL_PATH):
        webbrowser.open('file:///' + MANUAL_PATH.replace('\\', '/'))
    else:
        messagebox.showinfo('User manual', 'Manual file not found:\n%s' % MANUAL_PATH)


def show_about():
    messagebox.showinfo(
        'About QCS',
        'Quality Control System (SAGE)  %s\n\n'
        'Qualification and visualization of oceanographic sensor data\n'
        '(Seaguard/TSCP and HOBO Pendant loggers).' % data.QCS_VERSION)


def main(run=True):
    theme.enable_high_dpi()
    root = tk.Tk()
    root.title('Quality Control System (SAGE)  -  %s' % data.QCS_VERSION)
    theme.set_scaled_geometry(root, 1380, 860, min_width=1000, min_height=700)
    theme.apply_theme(root, viz.USER_PREFS.get('ui_theme', 'light'))
    theme.set_window_icon(root)

    # shared dark-mode state (the switch lives in the View menu)
    dark_mode = BooleanVar(value=viz.USER_PREFS.get('ui_theme', 'light') == 'dark')

    def toggle_theme():
        new_theme = 'dark' if dark_mode.get() else 'light'
        theme.apply_theme(root, new_theme)
        viz.USER_PREFS['ui_theme'] = new_theme   # shared dict -> qual sees it too
        viz.save_user_prefs()

    # --- notebook tabs + stacked content frames ---
    # Performance: a plain ttk.Notebook unmaps/remaps the WHOLE widget tree of a
    # tab on every switch, which is slow with sv-ttk on large tabs. Instead the
    # notebook holds two empty zero-height frames (just for the native tab look)
    # and the real content lives in two ALWAYS-MAPPED frames stacked in the same
    # grid cell; switching only calls tkraise(), which is instant.
    notebook = ttk.Notebook(root)
    notebook.pack(fill='x', padx=8, pady=(4, 0))
    theme.suppress_notebook_focus_ring(notebook)
    notebook.add(ttk.Frame(notebook, height=0), text='   Data Qualification   ')
    notebook.add(ttk.Frame(notebook, height=0), text='   Data Visualization   ')

    # ONE Execution log for the whole app, fixed at the bottom of the window:
    # every pipeline stage (qualification, Step 1 preview/build, Step 2 panels)
    # writes to the same panel - consistent position and message styling.
    app_log = theme.LogConsole(root, title=' Execution log ', height=7)
    app_log.frame.pack(side='bottom', fill='x', padx=8, pady=(0, 8))
    _out.set_sink(app_log.log)

    content = ttk.Frame(root)
    content.pack(fill='both', expand=True, padx=8, pady=(0, 8))
    content.rowconfigure(0, weight=1)
    content.columnconfigure(0, weight=1)
    qual_tab = ttk.Frame(content)
    viz_tab = ttk.Frame(content)
    qual_tab.grid(row=0, column=0, sticky='nsew')
    viz_tab.grid(row=0, column=0, sticky='nsew')

    qual.build_qualification_tab(qual_tab, root, shared_log=app_log)
    viz.build_visualization_tab(viz_tab, root, shared_log=app_log)

    # raise the selected tab's content (the log at the bottom never moves)
    def on_tab_changed(event=None):
        idx = notebook.index(notebook.select())
        (qual_tab if idx == 0 else viz_tab).tkraise()
    notebook.bind('<<NotebookTabChanged>>', on_tab_changed)
    on_tab_changed()  # start on the qualification tab

    def switch_to(idx):
        notebook.select(idx)

    def run_generate_panels():
        switch_to(1)
        root.update_idletasks()  # let the tab switch take effect before checking
        if viz._step2_frame is not None and viz._step2_frame.winfo_ismapped():
            viz.generatePanels()
        else:
            messagebox.showinfo('Generate Panels',
                                "Load a database first: on the Data Visualization "
                                "tab, choose the files and click 'Next'.")

    # --- menu bar (tailored to the pipeline) ---
    menubar = Menu(root)

    m_file = Menu(menubar, tearoff=0)
    m_file.add_command(label='Open Data File…  (Qualification)',
                       command=lambda: (switch_to(0), qual.selectFiles()))
    m_file.add_command(label='Open Database File(s)…  (Visualization)',
                       command=lambda: (switch_to(1), viz.selectFiles()))
    m_file.add_command(label='Set Output Folder…  (Qualification)',
                       command=lambda: (switch_to(0), qual.selectOutputFolder()))
    m_file.add_separator()
    m_file.add_command(label='Exit', command=root.destroy)
    menubar.add_cascade(label='File', menu=m_file)

    m_edit = Menu(menubar, tearoff=0)
    m_edit.add_command(label='Qualification Settings…', command=qual.open_settings_window)
    menubar.add_cascade(label='Edit', menu=m_edit)

    m_view = Menu(menubar, tearoff=0)
    m_view.add_checkbutton(label='Dark mode', variable=dark_mode, command=toggle_theme)
    m_view.add_separator()
    m_view.add_command(label='Go to Data Qualification', command=lambda: switch_to(0))
    m_view.add_command(label='Go to Data Visualization', command=lambda: switch_to(1))
    menubar.add_cascade(label='View', menu=m_view)

    m_tools = Menu(menubar, tearoff=0)
    m_tools.add_command(label='Run Qualification',
                        command=lambda: (switch_to(0), qual.start_qualification()))
    m_tools.add_command(label='Generate Panels', command=run_generate_panels)
    menubar.add_cascade(label='Tools', menu=m_tools)

    m_help = Menu(menubar, tearoff=0)
    m_help.add_command(label='User Manual', command=open_manual)
    m_help.add_command(label='Qualification Help', command=qual.show_help)
    m_help.add_command(label='Visualization Help', command=viz.show_help)
    m_help.add_separator()
    m_help.add_command(label='About', command=show_about)
    menubar.add_cascade(label='Help', menu=m_help)

    root.config(menu=menubar)
    if run:
        root.mainloop()
    return root, notebook


if __name__ == '__main__':
    main()
