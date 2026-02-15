#define MyAppName "BenchSim"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "BenchSim"
#define MyAppURL "https://github.com/lmcapacho/BenchSim"
#define MyAppExeName "BenchSim.exe"
#define MySourceDir "..\..\dist\BenchSim"

[Setup]
AppId={{3B93E26E-58E8-4FD0-AEAA-3AF54E108A28}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\BenchSim
DefaultGroupName=BenchSim
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist\installer
OutputBaseFilename=BenchSim-Setup-{#MyAppVersion}
SetupIconFile=..\..\benchsim\benchsim.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "{#MySourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\BenchSim"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\BenchSim"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch BenchSim"; Flags: nowait postinstall skipifsilent
