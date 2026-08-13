# -*- mode: python ; coding: utf-8 -*-
# PyInstaller recipe for the self-contained QCS build (the installer's payload).
#
# ONEDIR on purpose - never onefile: onefile unpacks the whole bundle (numpy,
# scipy, matplotlib...) into a temp folder on EVERY launch, with the antivirus
# scanning along, which is the classic 30-60 s startup. Onedir loads in place
# and opens in a few seconds. The v2.0-era specs (removed in v2.2.1) targeted
# the two separate tools; this one targets today's single entry point, QCS_App.
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
# sv_ttk ships .tcl theme files and gsw its coefficient tables; neither is a
# plain import PyInstaller can trace, so collect both wholesale.
for pkg in ('sv_ttk', 'gsw'):
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

a = Analysis(
    [os.path.join(SRC, 'QCS_App.py')],
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
