; Tailwind CSS Forge
; Script base de Inno Setup para instalar o bundle preparado em build\installer-bundle

#include "forge.version.iss"

#if DirExists(AddBackslash(SourcePath) + "..\..\..\app")
  #define MyBundleRoot AddBackslash(SourcePath) + "..\..\.."
#else
  #define MyBundleRoot AddBackslash(SourcePath) + "..\..\build\installer-bundle"
#endif

#define MySourceBundle MyBundleRoot
#define MyLicenseFile AddBackslash(MyBundleRoot) + "LICENSE"
#define MyOutputDir AddBackslash(MyBundleRoot) + "build\inno"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile={#MyLicenseFile}
OutputDir={#MyOutputDir}
OutputBaseFilename={#MyOutputBaseFilename}
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "{#MySourceBundle}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Executar {#MyAppName}"; Flags: nowait postinstall skipifsilent
