; Inno Setup recipe for the QCS installer.
;
; DUAL-MODE (v11.2): one setup.exe that asks whether to install for ALL USERS
; (Program Files, needs admin) or FOR ME ONLY (user area, no admin - what a
; field notebook without an administrator account uses). {autopf} resolves per
; choice. A Program Files install dir is read-only for regular users, which is
; fine: since v11.2 the app writes its settings and crash log to %APPDATA%\QCS
; whenever the install dir is not writable (QCS_Theme.writable_app_dir).
;
; CloseApplications lets the one-click self-update (QCS_Update) upgrade a
; running install; after a SILENT upgrade the app is relaunched by the [Run]
; entry gated on WizardSilent. Compile with ISCC.exe after the PyInstaller
; build; steps in README.md.

#define AppVersion "11.2"

[Setup]
AppId={{7B1C9D2E-4A31-4F5B-9C1E-QCSSAGE00001}
AppName=QCS - Quality Control System (SAGE)
AppVersion={#AppVersion}
AppPublisher=SAGE (COPPE/UFRJ)
DefaultDirName={autopf}\QCS
DefaultGroupName=QCS
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputBaseFilename=QCS_Setup_v{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=QCS - Quality Control System (SAGE)
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
