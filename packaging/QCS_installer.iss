; Inno Setup recipe for the QCS installer.
;
; DUAL-MODE, Program Files by DEFAULT (owner decision, 2026-08-13): the wizard
; opens preselected on "install for all users" -> C:\Program Files\QCS (this is
; a 64-bit app, so plain Program Files is its correct home; the (x86) folder is
; the convention for 32-bit programs). "Only for me" remains available in the
; same dialog for machines without an administrator account - the field
; notebook - landing in the user area. A Program Files install dir is read-only
; for regular users, which is fine: since v11.2 the app writes its settings and
; crash log to %APPDATA%\QCS whenever the install dir is not writable
; (QCS_Theme.writable_app_dir).
;
; Self-update note: an upgrade reuses the PREVIOUS install's mode and folder
; (UsePreviousPrivileges/UsePreviousAppDir, both default) - over a Program
; Files install the silent upgrade shows one UAC prompt, over a per-user
; install it stays fully silent.
;
; CloseApplications lets the one-click self-update (QCS_Update) upgrade a
; running install; after a SILENT upgrade the app is relaunched by the [Run]
; entry gated on WizardSilent. Compile with ISCC.exe after the PyInstaller
; build; steps in README.md.

#define AppVersion "12.0"

[Setup]
AppId={{7B1C9D2E-4A31-4F5B-9C1E-QCSSAGE00001}
AppName=QCS - Quality Control System (SAGE)
AppVersion={#AppVersion}
AppPublisher=SAGE (COPPE/UFRJ)
DefaultDirName={autopf}\QCS
DefaultGroupName=QCS
DisableProgramGroupPage=yes
; The folder page stays on Inno's default 'auto': shown on a FRESH install,
; hidden when a previous install is found, so an upgrade keeps its folder
; without asking (owner, v12.1 - the v12.1 first draft forced it always on
; and the owner asked for the old rule back).
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
OutputBaseFilename=QCS_Setup_v{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=QCS - Quality Control System (SAGE)
SetupIconFile=..\sourceCode\qcs_icon.ico
UninstallDisplayIcon={app}\QCS.exe
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; the PyInstaller onedir output, produced into dist\QCS next to this script
Source: "dist\QCS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\QCS"; Filename: "{app}\QCS.exe"
Name: "{group}\QCS User Manual"; Filename: "{app}\Quality Control System (SAGE) - User Manual.html"
Name: "{autodesktop}\QCS"; Filename: "{app}\QCS.exe"; Tasks: desktopicon

[Run]
; the two Finish-page checkboxes (v12.1, owner request): open the manual and
; start the program. 'postinstall' is what makes them checkboxes; the manual
; needs shellexec because it is an .html, not an executable.
Filename: "{app}\Quality Control System (SAGE) - User Manual.html"; Description: "Open the user manual"; Flags: postinstall shellexec skipifsilent nowait unchecked
Filename: "{app}\QCS.exe"; Description: "{cm:LaunchProgram,QCS}"; Flags: nowait postinstall skipifsilent
; a SILENT run is the self-update path (QCS_Update passes /SILENT): the app
; closed itself to let the installer work, so reopen it updated
Filename: "{app}\QCS.exe"; Flags: nowait; Check: WizardSilent

[UninstallDelete]
; the app writes these beside the exe at runtime (user-area installs); remove
; them so an uninstall leaves nothing behind (preferences and a crash log, not
; user data). Program Files installs keep them in %APPDATA%\QCS instead, which
; is left alone - it may serve a future reinstall.
Type: files; Name: "{app}\qcs_user_settings.json"
Type: files; Name: "{app}\QCS_crash.log"
