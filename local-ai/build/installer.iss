; מתקין של "גאון – עוזר AI מקומי"
#define AppName "גאון - עוזר AI מקומי"
#define AppVer GetEnv("GAON_VERSION")
#if AppVer == ""
  #define AppVer "1.0.0"
#endif
#define HebrewIsl AddBackslash(CompilerPath) + "Languages\Hebrew.isl"

[Setup]
AppId={{7C1F3E52-9B4A-4E7B-A0D2-6A1E0C5B9F11}
AppName={#AppName}
AppVersion={#AppVer}
AppPublisher=Gaon
DefaultDirName={code:DefaultInstallDir}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\build\out
OutputBaseFilename=Gaon-Setup
SetupIconFile=..\assets\gaon.ico
UninstallDisplayIcon={app}\Gaon.exe
Compression=lzma2/fast
SolidCompression=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
; המודל עצמו (15-23GB) יורד בתוך התוכנה
ExtraDiskSpaceRequired=21474836480

[Languages]
#if FileExists(HebrewIsl)
Name: "he"; MessagesFile: "compiler:Languages\Hebrew.isl"
#else
Name: "en"; MessagesFile: "compiler:Default.isl"
#endif

[Tasks]
Name: "desktopicon"; Description: "צור קיצור דרך בשולחן העבודה"; Flags: checkedonce

[Files]
Source: "..\build\dist\Gaon\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\models"
Name: "{app}\פרויקטים"

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\Gaon.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Gaon.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Gaon.exe"; Description: "הפעל את גאון עכשיו"; Flags: nowait postinstall skipifsilent

[Code]
function DefaultInstallDir(Param: String): String;
begin
  if DirExists('F:\') then
    Result := 'F:\2222222222222222222222222\Gaon'
  else
    Result := ExpandConstant('{localappdata}\Programs\Gaon');
end;
