#define MyAppName "GroveScan"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "GroveScan Solutions"
#define MyAppURL "https://github.com/mosesoghene/GroveScan"
#define MyAppExeName "GroveScan.exe"
#define MyAppId "{D5A12B8E-4F3C-4A9B-8E2F-6C1A7B9D3E5F}"

[Setup]
AppId={{#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=LICENSE.txt
InfoBeforeFile=README.txt
OutputDir=dist\installer
OutputBaseFilename=GroveScan_Setup_v{#MyAppVersion}
SetupIconFile=assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0.17763
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Installer
VersionInfoCopyright=Copyright (C) 2024 {#MyAppPublisher}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main executable and Python runtime
Source: "dist\GroveScan\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\GroveScan\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

; Application assets (if they exist)
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: DirExists('assets')

; Default settings template
Source: "default_settings.json"; DestDir: "{app}"; DestName: "default_settings.json"; Flags: ignoreversion

; Documentation
Source: "README.txt"; DestDir: "{app}"; DestName: "README.txt"; Flags: ignoreversion
Source: "LICENSE.txt"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Registry]
; Store installation path for uninstaller
Root: HKLM; Subkey: "SOFTWARE\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
; File associations for profile files
Root: HKCR; Subkey: ".dsprofile"; ValueType: string; ValueName: ""; ValueData: "GroveScanProfile"; Flags: uninsdeletevalue
Root: HKCR; Subkey: "GroveScanProfile"; ValueType: string; ValueName: ""; ValueData: "GroveScan Profile"; Flags: uninsdeletekey
Root: HKCR; Subkey: "GroveScanProfile\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCR; Subkey: "GroveScanProfile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Run]
; Optionally run the application after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Stop the application before uninstalling
Filename: "taskkill"; Parameters: "/F /IM {#MyAppExeName}"; RunOnceId: "StopApp"; Flags: runhidden

[UninstallDelete]
; Clean up temporary files in installation directory
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\*.tmp"
Type: dirifempty; Name: "{app}\temp"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  UserDocumentsDir: String;
  UserAppDataDir: String;
  UserLocalAppDataDir: String;
  ProfilesDir: String;
  SettingsFile: String;
  DefaultSettingsFile: String;
  LogsDir: String;
  ExportTemplatesDir: String;
begin
  if CurStep = ssPostInstall then
  begin
    // Get user directories
    UserDocumentsDir := ExpandConstant('{userdocs}\GroveScan');
    UserAppDataDir := ExpandConstant('{userappdata}\GroveScan');
    UserLocalAppDataDir := ExpandConstant('{localappdata}\GroveScan');

    // Define specific directories
    ProfilesDir := UserDocumentsDir + '\Profiles';
    ExportTemplatesDir := UserDocumentsDir + '\Export Templates';
    LogsDir := UserLocalAppDataDir + '\Logs';

    // Settings file paths
    SettingsFile := UserAppDataDir + '\settings.json';
    DefaultSettingsFile := ExpandConstant('{app}\default_settings.json');

    // Create user directories
    ForceDirectories(UserDocumentsDir);
    ForceDirectories(ProfilesDir);
    ForceDirectories(ExportTemplatesDir);
    ForceDirectories(UserAppDataDir);
    ForceDirectories(UserLocalAppDataDir);
    ForceDirectories(LogsDir);

    // Create initial settings file if it doesn't exist
    if not FileExists(SettingsFile) and FileExists(DefaultSettingsFile) then
    begin
      FileCopy(DefaultSettingsFile, SettingsFile, False);
    end;

    // Create welcome profile directory marker
    SaveStringToFile(ProfilesDir + '\README.txt',
      'GroveScan Profiles' + #13#10 +
      '========================' + #13#10 + #13#10 +
      'This folder contains your scanning profiles.' + #13#10 +
      'Profiles define the structure and organization of your scanned documents.' + #13#10 + #13#10 +
      'You can:' + #13#10 +
      '- Create new profiles in the application' + #13#10 +
      '- Import/export profiles as JSON files' + #13#10 +
      '- Back up this folder to preserve your configurations' + #13#10 + #13#10 +
      'Each profile (.json file) contains:' + #13#10 +
      '- Index field definitions (folder structure, filename components)' + #13#10 +
      '- Default scanner settings (resolution, color mode, format)' + #13#10 +
      '- Export preferences (PDF quality, folder creation options)' + #13#10 + #13#10 +
      'Generated by GroveScan v' + ExpandConstant('{#MyAppVersion}'), False);

    // Create export templates directory marker
    SaveStringToFile(ExportTemplatesDir + '\README.txt',
      'GroveScan Export Templates' + #13#10 +
      '================================' + #13#10 + #13#10 +
      'This folder contains your custom export templates.' + #13#10 +
      'Export templates define how your documents are saved (PDF, TIFF, etc.).' + #13#10 + #13#10 +
      'The application includes built-in templates:' + #13#10 +
      '- High Quality PDF (ReportLab engine, professional output)' + #13#10 +
      '- Fast PDF (PIL engine, quick processing)' + #13#10 +
      '- Archive TIFF (multi-page, lossless compression)' + #13#10 +
      '- Web Images (PNG format for online use)' + #13#10 +
      '- Letter/A4 PDF (standard page sizes with margins)' + #13#10 +
      '- Email Friendly (compressed, timestamp-enabled)' + #13#10 + #13#10 +
      'You can create custom templates and save them here.' + #13#10 + #13#10 +
      'Generated by GroveScan v' + ExpandConstant('{#MyAppVersion}'), False);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  UserDocumentsDir: String;
  UserAppDataDir: String;
  UserLocalAppDataDir: String;
  ResponseCode: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    UserDocumentsDir := ExpandConstant('{userdocs}\GroveScan');
    UserAppDataDir := ExpandConstant('{userappdata}\GroveScan');
    UserLocalAppDataDir := ExpandConstant('{localappdata}\GroveScan');

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  UserDocumentsDir: String;
  UserAppDataDir: String;
  UserLocalAppDataDir: String;
  ResponseCode: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    UserDocumentsDir := ExpandConstant('{userdocs}\GroveScan');
    UserAppDataDir := ExpandConstant('{userappdata}\GroveScan');
    UserLocalAppDataDir := ExpandConstant('{localappdata}\GroveScan');

    // Ask if user wants to keep their data
    ResponseCode := MsgBox(
      'Do you want to keep your scanning profiles, settings, and data?' + #13#13 +
      'Select "Yes" to keep your data for future installations.' + #13 +
      'Select "No" to remove all application data.' + #13#13 +
      'Data locations:' + #13 +
      'Profiles: ' + UserDocumentsDir + #13 +
      'Settings: ' + UserAppDataDir + #13 +
      'Logs: ' + UserLocalAppDataDir,
      mbConfirmation, MB_YESNO or MB_DEFBUTTON1);

    if ResponseCode = IDNO then
    begin
      // User chose to remove all data
      DelTree(UserDocumentsDir, True, True, True);
      DelTree(UserAppDataDir, True, True, True);
      DelTree(UserLocalAppDataDir, True, True, True);
    end;
  end;
end;

function InitializeSetup(): Boolean;
var
  Version: TWindowsVersion;
begin
  GetWindowsVersionEx(Version);

  // Check Windows version (Windows 10 version 1809 or later)
  if (Version.Major < 10) or ((Version.Major = 10) and (Version.Build < 17763)) then
  begin
    MsgBox('This application requires Windows 10 version 1809 (build 17763) or later.' + #13#13 +
           'Please update your Windows installation and try again.',
           mbError, MB_OK);
    Result := False;
  end
  else
  begin
    Result := True;
  end;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
end;

function DirExists(const DirName: String): Boolean;
begin
  Result := DirExists(ExpandConstant(DirName));
end;