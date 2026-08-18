# -*- mode: python ; coding: utf-8 -*-
# PyInstaller recipe for the self-contained QCS build (the installer's payload).
#
# ONEDIR on purpose - never onefile: onefile unpacks the whole bundle (numpy,
# scipy, matplotlib...) into a temp folder on EVERY launch, with the antivirus
# scanning along, which is the classic 30-60 s startup. Onedir loads in place
# and opens in a few seconds.
#
# v12.0: the entry point is the Qt shell (QCS_QtApp, PySide6 6.8.3 - newer
# PySide6 needs an MSVC runtime older field machines may lack). tkinter STILL
# ships: the pipeline closures are materialized on a hidden tk root (the
# batch-driver pattern); removing tk entirely is a post-port cleanup.
#
# Build from a CLEAN pip venv, not from Anaconda: conda numpy/scipy link MKL,
# which roughly doubles the bundle for nothing the app needs. The exact build
# steps live in packaging/README.md.
#
# The user manual is NOT listed in datas: datas land inside _internal/, while
# QCS_App resolves the manual at the app root (two dirname()s up from the
# frozen module, which is _internal/..). The build step copies it beside the
# exe instead - see README.md - so the source needs no frozen-mode special
# case and QCS_VERSION does not move for packaging.
import os

from PyInstaller.utils.hooks import collect_all

SRC = os.path.join(SPECPATH, '..', 'sourceCode')  # noqa: F821 (SPECPATH is a PyInstaller global)

datas, binaries, hiddenimports = [], [], []
# sv_ttk ships .tcl theme files, gsw its coefficient tables and certifi the CA
# bundle (cacert.pem) the update check validates against; none of the three is
# a plain import PyInstaller can trace, so collect them wholesale. certifi is
# what frees the app from the target machine's certificate store - see
# QCS_Update.ssl_context.
# tkinterdnd2 ships the tkdnd Tcl library as data files (loaded at runtime by
# TkinterDnD._require), so it must be collected wholesale like sv_ttk.
for pkg in ('sv_ttk', 'gsw', 'certifi', 'tkinterdnd2'):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h
# The window/taskbar icons: set_window_icon resolves them beside QCS_Theme
# (dirname(__file__) = _internal when frozen), so they must ship as datas -
# without this the installed app silently falls back to the Tk feather.
datas += [(os.path.join(SRC, 'qcs_icon.ico'), '.'),
          (os.path.join(SRC, 'qcs_icon.png'), '.')]
# pandas imports its Excel engine lazily; make it explicit (the v2.2-era spec
# needed the same).
hiddenimports += ['openpyxl', 'openpyxl.cell._writer']
# matplotlib loads the SVG renderer lazily on the first savefig('*.svg') -
# and EVERY plot the app writes (light window, DataView panels, Doppler) is
# an .svg. Without this the installed app dies at the end of the first real
# qualification with "No module named 'matplotlib.backends.backend_svg'"
# (found by the owner on the first end-to-end run of an installed copy,
# v11.4.1 - the smoke test only launches the window, it never qualifies).
# (backend_agg and backend_mixed ride along: a real-run import trace shows
# savefig pulls all three, and hook behavior may change between versions)
hiddenimports += ['matplotlib.backends.backend_svg',
                  'matplotlib.backends.backend_mixed',
                  'matplotlib.backends.backend_agg']
# the Qt shell selects the QtAgg backend at startup (matplotlib.use('QtAgg')),
# another lazy import the static trace cannot see
hiddenimports += ['matplotlib.backends.backend_qtagg']

a = Analysis(
    [os.path.join(SRC, 'QCS_QtApp.py')],
    pathex=[SRC],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='QCS',
    console=False,               # windowed: errors go to the in-app log / crash handler
    upx=False,                   # UPX-compressed DLLs trip antivirus for no real gain
    # embedded in the exe itself: Explorer, the Desktop/Start Menu shortcuts
    # and the taskbar pin all read THIS icon, not the runtime one
    icon=os.path.join(SRC, 'qcs_icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name='QCS',
    upx=False,
)
