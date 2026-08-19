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
; Files install it shows one UAC prompt, over a per-user install none.
;
; CloseApplications lets the one-click self-update (QCS_Update) upgrade a
; running install. Since v12.2.1 that update runs the WIZARD, not /SILENT: the
; silent path's only way back into the app was the [Run] entry gated on
; WizardSilent, and that relaunch failed on the owner's machine twice with
; nothing to show why, so the reopening became a finish-page checkbox the
; operator can see. Compile with ISCC.exe after the PyInstaller build; steps
; in README.md.

#define AppVersion "12.2.2"

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

[CustomMessages]
; Spelled out rather than Inno's own {cm:LaunchProgram} ('Launch QCS'): after
; an update the finish page IS the reopening, so the checkbox has to say when
; it happens (owner, 2026-08-19).
english.LaunchAfterInstall=Launch QCS after installation
brazilianportuguese.LaunchAfterInstall=Abrir o QCS após a instalação

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; the PyInstaller onedir output, produced into dist\QCS next to this script
; Excludes: the app writes these two beside the exe at runtime, and the
; recipe's own smoke test (step 4) runs the app inside dist\QCS - v12.2 shipped
; the build machine's settings file because of it. Excluding them makes the
; payload independent of whether the bundle was smoke-tested before compiling.
Source: "dist\QCS\*"; DestDir: "{app}"; Excludes: "qcs_user_settings.json,QCS_crash.log"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\QCS"; Filename: "{app}\QCS.exe"
Name: "{group}\QCS User Manual"; Filename: "{app}\Quality Control System (SAGE) - User Manual.html"
Name: "{autodesktop}\QCS"; Filename: "{app}\QCS.exe"; Tasks: desktopicon

[Run]
; the two Finish-page checkboxes (v12.1, owner request): open the manual and
; start the program. 'postinstall' is what makes them checkboxes; the manual
; needs shellexec because it is an .html, not an executable.
Filename: "{app}\Quality Control System (SAGE) - User Manual.html"; Description: "Open the user manual"; Flags: postinstall shellexec skipifsilent nowait unchecked
; runasoriginaluser on BOTH: an install into Program Files runs elevated, and
; an app started from here inherits that token. Windows then blocks drag-and-
; drop from Explorer into it (UIPI: a lower integrity level cannot post to a
; higher one) - the app looked broken until it was reopened from its shortcut
; (owner, 2026-08-18, confirmed on the v12.1 install).
; skipifsilent stays: without it this entry would ALSO run under /SILENT (where
; there is no finish page to tick) and the app would be started twice.
Filename: "{app}\QCS.exe"; Description: "{cm:LaunchAfterInstall}"; Flags: nowait postinstall skipifsilent runasoriginaluser
; kept for a hand-run '/SILENT' install, which has no finish page and so no
; checkbox. The self-update no longer takes this path: it runs the wizard
; precisely so the operator gets the checkbox above (owner, 2026-08-19).
Filename: "{app}\QCS.exe"; Flags: nowait runasoriginaluser; Check: WizardSilent

[UninstallDelete]
; the app writes these beside the exe at runtime (user-area installs); remove
; them so an uninstall leaves nothing behind (preferences and a crash log, not
; user data). Program Files installs keep them in %APPDATA%\QCS instead, which
; is left alone - it may serve a future reinstall.
Type: files; Name: "{app}\qcs_user_settings.json"
Type: files; Name: "{app}\QCS_crash.log"
