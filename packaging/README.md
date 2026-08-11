# Packaging — the QCS installer

Builds a self-contained Windows installer so a field notebook needs **no
Python, no Anaconda and no dependencies**. Two stages: PyInstaller produces a
`--onedir` bundle (the payload), Inno Setup wraps it into `QCS_Setup_vX.Y.exe`.

The v2.0 release shipped PyInstaller executables and v2.2 dropped them for
script execution; this recipe brings packaging back on today's layout (the
single `QCS_App.py` entry point). **No source change is needed**: the
frozen-aware paths from the v2.0 era survived (`settings_store_path`, the
crash handler), so packaging never moves `QCS_VERSION`.

## Decisions that keep the startup fast

- **`--onedir`, never `--onefile`.** Onefile unpacks the entire bundle into a
  temp folder on every launch — with numpy/scipy/matplotlib and the antivirus
  scanning along, that is the classic 30–60 s startup. Onedir loads in place.
- **Build from a clean pip venv, not from Anaconda.** Conda's numpy/scipy link
  MKL, which roughly doubles the bundle for nothing the app uses.
- **No UPX.** Compressed DLLs trip antivirus heuristics for marginal size gain.
- **Install to `{localappdata}\QCS`, `PrivilegesRequired=lowest`.** No admin
  account needed on the notebook, and the folder is user-writable — which is
  where the frozen app expects to write its settings and crash log (beside the
  exe).

## Build steps (from the repository root)

```powershell
# 1. clean build venv (once)
& "C:\Users\LAMB\anaconda3\python.exe" -m venv "$env:TEMP\qcs_build_env"
& "$env:TEMP\qcs_build_env\Scripts\python.exe" -m pip install numpy pandas matplotlib scipy openpyxl gsw sv-ttk pyinstaller

# 2. the onedir bundle -> packaging\dist\QCS\
#    The PATH line is LOAD-BEARING: the venv is built on Anaconda's Python,
#    whose extension modules (_ctypes, _ssl, tkinter...) load their DLLs
#    (ffi-8.dll, libssl, tcl86t...) from anaconda3\Library\bin. Without that
#    folder on PATH the dependency scan cannot see them, the DLLs are not
#    bundled, and the frozen app dies at startup with
#    "DLL load failed while importing _ctypes".
$env:PATH = "C:\Users\LAMB\anaconda3\Library\bin;" + $env:PATH
& "$env:TEMP\qcs_build_env\Scripts\pyinstaller.exe" packaging\QCS.spec --noconfirm --distpath packaging\dist --workpath "$env:TEMP\qcs_build_work"

# 3. the manual goes BESIDE the exe (not in datas: datas land in _internal\,
#    while the app resolves the manual at the app root - two dirname()s up
#    from the frozen module)
Copy-Item "Quality Control System (SAGE) - User Manual.html" packaging\dist\QCS\

# 4. smoke test: launch, confirm the window appears in a few seconds, close
packaging\dist\QCS\QCS.exe

# 5. the installer -> packaging\Output\QCS_Setup_vX.Y.exe
#    (Inno Setup installed per-user - no admin - via: innosetup-6.x.exe /VERYSILENT /CURRENTUSER)
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" packaging\QCS_installer.iss
```

`packaging\dist\`, `packaging\Output\` and the venv are build artifacts —
gitignored, rebuilt at will. Only the two recipes and this README are tracked.

## When a new version is released

Update `#define AppVersion` in `QCS_installer.iss` to match `QCS_VERSION`,
rebuild the two stages, and ship the new `QCS_Setup_vX.Y.exe`. Installing over
an existing install upgrades it in place; the version-gated settings reset
then behaves exactly as on a source install (dialog on first launch, v11.1).

## Measured on the reference build (2026-08-11)

- Bundle: ~195 MB onedir; installer compresses it to a single `setup.exe`.
- Startup: **~3 s warm**. The very first launch on a machine takes ~20 s while
  matplotlib builds its font cache (one-time, persisted per user) — tell the
  field crew so nobody thinks it hung.
- Always rebuild with `--clean` after changing the environment or the spec:
  a cached analysis silently reuses the old dependency scan (that is how the
  missing-DLL fix looked like it had failed).

## Known limits

- The installer carries no code-signing certificate, so SmartScreen may warn
  on first run ("More info → Run anyway"). Expected; signing needs a paid
  certificate.
- The bundle has no window icon: the project's `.ico` files were removed in
  v2.2.1. If an icon returns to the repo, add `icon=` to the EXE() in
  `QCS.spec` and `SetupIconFile=` to the `.iss`.
