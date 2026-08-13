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
import QCS_Update as updater

# Both tools share ONE preferences dict, so saving from either tab writes the
# same qcs_user_settings.json without clobbering the other tab's keys.
qual.USER_PREFS = viz.USER_PREFS

theme.install_crash_handler('QCS', _out, base_dir=theme.writable_app_dir())

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
    notebook.add(ttk.Frame(notebook, height=0), text='   Data qualification   ')
    notebook.add(ttk.Frame(notebook, height=0), text='   Data visualization   ')

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

    # Raise the selected tab's content (the log at the bottom never moves).
    # NOTE: this must be the ONLY <<NotebookTabChanged>> binding - a second
    # bind() replaces the first, which is how the dashed focus ring once came
    # back (it clobbered suppress_notebook_focus_ring's binding). The ring fix
    # is folded in here: moving focus onto the raised frame (frames draw no
    # focus ring) takes it off the notebook's tab label.
    def on_tab_changed(event=None):
        idx = notebook.index(notebook.select())
        frame = qual_tab if idx == 0 else viz_tab
        frame.tkraise()
        frame.focus_set()
        # after a qualification run, pre-select the just-made file in Visualization
        if idx == 1 and getattr(qual, 'PENDING_VIZ_PREFILL', None):
            viz.apply_pending_prefill(qual.PENDING_VIZ_PREFILL)
            qual.PENDING_VIZ_PREFILL = None
    notebook.bind('<<NotebookTabChanged>>', on_tab_changed)
    # clicking the ALREADY selected tab fires no <<NotebookTabChanged>>, so also
    # defocus on plain clicks (separate event: does not clobber the bind above)
    notebook.bind('<ButtonRelease-1>', lambda e: on_tab_changed(), add='+')
    on_tab_changed()  # start on the qualification tab

    def switch_to(idx):
        notebook.select(idx)

    def run_generate_panels():
        switch_to(1)
        root.update_idletasks()  # let the tab switch take effect before checking
        if viz._step2_frame is not None and viz._step2_frame.winfo_ismapped():
            viz.generatePanels()
        else:
            messagebox.showinfo('Generate panels',
                                "Load a database first: on the Data Visualization "
                                "tab, choose the files and click 'Next'.")

    # --- menu bar (tailored to the pipeline) ---
    menubar = Menu(root)

    m_file = Menu(menubar, tearoff=0)
    m_file.add_command(label='Open data file…  (qualification)',
                       command=lambda: (switch_to(0), qual.selectFiles()))
    m_file.add_command(label='Open database file(s)…  (visualization)',
                       command=lambda: (switch_to(1), viz.selectFiles()))
    m_file.add_command(label='Set output folder…  (qualification)',
                       command=lambda: (switch_to(0), qual.selectOutputFolder()))
    m_file.add_separator()
    m_file.add_command(label='Exit', command=root.destroy)
    menubar.add_cascade(label='File', menu=m_file)

    m_edit = Menu(menubar, tearoff=0)
    m_edit.add_command(label='Qualification settings…', command=qual.open_settings_window)
    menubar.add_cascade(label='Edit', menu=m_edit)

    m_view = Menu(menubar, tearoff=0)
    m_view.add_checkbutton(label='Dark mode', variable=dark_mode, command=toggle_theme)
    m_view.add_separator()
    m_view.add_command(label='Go to data qualification', command=lambda: switch_to(0))
    m_view.add_command(label='Go to data visualization', command=lambda: switch_to(1))
    menubar.add_cascade(label='View', menu=m_view)

    m_tools = Menu(menubar, tearoff=0)
    m_tools.add_command(label='Run qualification',
                        command=lambda: (switch_to(0), qual.start_qualification()))
    m_tools.add_command(label='Generate panels', command=run_generate_panels)
    menubar.add_cascade(label='Tools', menu=m_tools)

    def manual_update_check():
        latest = updater.fetch_latest()
        if latest is None:
            messagebox.showwarning(
                'Check for updates',
                'The releases page could not be reached - no connection, or '
                'GitHub is unavailable. Try again later.')
        elif updater.is_newer(latest['tag'], data.QCS_VERSION):
            updater.offer_update(latest, root)
        else:
            messagebox.showinfo(
                'Check for updates',
                'You are up to date: %s is the latest release.' % data.QCS_VERSION)

    m_help = Menu(menubar, tearoff=0)
    m_help.add_command(label='User manual', command=open_manual)
    m_help.add_command(label='Qualification help', command=qual.show_help)
    m_help.add_command(label='Visualization help', command=viz.show_help)
    m_help.add_separator()
    m_help.add_command(label='Check for updates…', command=manual_update_check)
    m_help.add_command(label='About', command=show_about)
    menubar.add_cascade(label='Help', menu=m_help)

    root.config(menu=menubar)

    # Startup update check (v11.2): a daemon thread queries the releases API
    # and speaks ONLY when a newer version exists - offline (the field
    # notebook's normal state) it times out and stays silent. The callback
    # hops onto the Tk main thread via after(); Tk calls from a worker thread
    # are not safe.
    updater.check_in_background(
        data.QCS_VERSION,
        lambda latest: root.after(0, lambda: updater.offer_update(latest, root)))

    # First launch after a version change: the saved QC criteria were reset to
    # the new version's defaults (by design - see load_user_prefs), but until
    # v11.1 the only trace was a log line, easy to miss before qualifying. The
    # dialog lives HERE, not in load_user_prefs, so the headless/batch paths
    # (which drive QCS_Main directly and never import this shell) cannot block
    # on it. after() defers it until the window is actually up.
    if getattr(qual, 'SETTINGS_RESET_FROM', None):
        root.after(300, lambda: messagebox.showinfo(
            'Quality criteria reset to the %s defaults' % data.QCS_VERSION,
            'Your saved settings were from %s, so the QC criteria were reset to '
            'the %s defaults - a version may change criteria on purpose, and '
            'keeping the old saved values would silently mask that.\n\n'
            'Folders, file choices and visualization preferences were kept. '
            'Custom criteria can be set again in Edit > Qualification settings; '
            'they will persist within %s.'
            % (qual.SETTINGS_RESET_FROM, data.QCS_VERSION, data.QCS_VERSION)))

    if run:
        root.mainloop()
    return root, notebook


if __name__ == '__main__':
    main()
