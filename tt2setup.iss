; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

; Change this base path to your needs
#define ProjectBaseDir "D:\Users\robert\Projects\teamtactics"

#define MyAppName "TeamTactics2"
#define MyAppVersion "0.98"
#define MyAppPublisher "Bausdorf engineering"
#define MyAppURL "https://github.com/robbyb67/simracing/tree/master/team-tactics"
#define MyAppExeName "teamtactics2.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{EBE69E27-FCE2-4433-B53E-A2C07A396E73}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
InfoAfterFile={#ProjectBaseDir}\LICENSE
; Uncomment the following line to run in non administrative install mode (install for current user only.)
;PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir={#ProjectBaseDir}\dist
OutputBaseFilename=TeamTactics2Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#ProjectBaseDir}\dist\teamtactics2.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjectBaseDir}\dist\irtactics.ini"; DestDir: "{app}"; Flags: ignoreversion comparetimestamp
Source: "{#ProjectBaseDir}\dist\liesmich.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjectBaseDir}\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\irtactics.ini"; Description: "Edit configuration"; Flags: postinstall shellexec waituntilterminated skipifsilent
Filename: "{app}\teamtactics2.exe"; Description: "Launch application"; Flags: postinstall nowait skipifsilent
