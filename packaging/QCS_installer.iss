; Inno Setup recipe for the QCS installer.
;
; Installs to the USER area ({localappdata}\QCS) with PrivilegesRequired=lowest,
; so a field notebook needs no administrator account - and the app can keep
; writing its settings and crash log beside the exe, which is where the code
; already puts them when frozen (settings_store_path, install_crash_handler).
; Compile with ISCC.exe after the PyInstaller build; steps in README.md.

#define AppVersion "11.1"

[Setup]
AppId={{7B1C9D2E-4A31-4F5B-9C1E-QCSSAGE00001}
AppName=QCS - Quality Control System (SAGE)
AppVersion={#AppVersion}
AppPublisher=SAGE (COPPE/UFRJ)
DefaultDirName={localappdata}\QCS
DefaultGroupName=QCS
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputBaseFilename=QCS_Setup_v{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=QCS - Quality Control System (SAGE)

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

[UninstallDelete]
; the app writes these beside the exe at runtime; remove them so an uninstall
; leaves nothing behind (they are preferences and a crash log, not user data)
Type: files; Name: "{app}\qcs_user_settings.json"
Type: files; Name: "{app}\QCS_crash.log"
