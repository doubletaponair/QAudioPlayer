; Inno Setup script for QAudioPlayer
;
; PER-USER install (no administrator rights / no UAC required).
;   - Installs into %LOCALAPPDATA%\QAudioPlayer
;   - All registry writes go to HKCU (via Inno's HKA auto-root, which resolves
;     to HKEY_CURRENT_USER when PrivilegesRequired=lowest)
;
; This matches the in-app auto-updater: because the exe lives in a user-writable
; location, QAudioPlayer can replace itself on update with no elevation prompt.
; Do NOT switch this back to a Program Files / HKLM (admin) install without also
; reworking the updater, or every auto-update will require UAC and likely fail.
;
; Architecture / OS support:
;   - Windows 10 x64 (build 17763 / 1809 and later) and Windows 11 x64
;   - ARM64 Windows runs the x64 exe under built-in emulation (transparent)
;
; Build: compile with Inno Setup 6.3 or later (6.7+ recommended), e.g.
;        ISCC.exe installer.iss
;
; Output: Output\QAudioPlayerSetup.exe

#define AppName       "QAudioPlayer"
#define AppVersion    "1.0.1"
#define AppPublisher  "QAudioPlayer"
#define AppExeName    "QAudioPlayer.exe"

[Setup]
AppId={{B8A73F2C-4F8E-4A3B-9B21-7CE5B4D3F2A1}}
AppName={#AppName}
AppVersion={#AppVersion}
VersionInfoVersion={#AppVersion}.0
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\QAudioPlayer
DefaultGroupName={#AppName}
OutputDir=Output
OutputBaseFilename=QAudioPlayerSetup
Compression=lzma
SolidCompression=yes

; x64compatible: allow install on x64 and on ARM64 (via x64 emulation).
; Requires Inno Setup 6.3 or later - it will refuse to compile otherwise.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Require Windows 10 1809 (build 17763) or later.
MinVersion=10.0.17763

; Per-user install: no elevation. HKA registry root resolves to HKCU.
PrivilegesRequired=lowest
ChangesAssociations=yes
WizardStyle=modern
DisableWelcomePage=no

UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"
Name: "registerdefault"; Description: "Register as an available default app for media files"; GroupDescription: "File associations:"; Flags: checkedonce

[Files]
Source: "dist\QAudioPlayer.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
; ProgID for the file handler (HKA -> HKCU\Software\Classes for a per-user install)
Root: HKA; Subkey: "Software\Classes\QAudioPlayer.MediaFile"; ValueType: string; ValueName: ""; ValueData: "QAudioPlayer - Media File"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\QAudioPlayer.MediaFile\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExeName},0"
Root: HKA; Subkey: "Software\Classes\QAudioPlayer.MediaFile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""

; "Open with" entries for audio formats
Root: HKA; Subkey: "Software\Classes\.mp3\OpenWithProgids"; ValueType: string; ValueName: "QAudioPlayer.MediaFile"; ValueData: ""; Flags: uninsdeletevalue; Tasks: registerdefault
Root: HKA; Subkey: "Software\Classes\.wav\OpenWithProgids"; ValueType: string; ValueName: "QAudioPlayer.MediaFile"; ValueData: ""; Flags: uninsdeletevalue; Tasks: registerdefault
Root: HKA; Subkey: "Software\Classes\.m4a\OpenWithProgids"; ValueType: string; ValueName: "QAudioPlayer.MediaFile"; ValueData: ""; Flags: uninsdeletevalue; Tasks: registerdefault
Root: HKA; Subkey: "Software\Classes\.aac\OpenWithProgids"; ValueType: string; ValueName: "QAudioPlayer.MediaFile"; ValueData: ""; Flags: uninsdeletevalue; Tasks: registerdefault
Root: HKA; Subkey: "Software\Classes\.flac\OpenWithProgids"; ValueType: string; ValueName: "QAudioPlayer.MediaFile"; ValueData: ""; Flags: uninsdeletevalue; Tasks: registerdefault
Root: HKA; Subkey: "Software\Classes\.ogg\OpenWithProgids"; ValueType: string; ValueName: "QAudioPlayer.MediaFile"; ValueData: ""; Flags: uninsdeletevalue; Tasks: registerdefault
Root: HKA; Subkey: "Software\Classes\.opus\OpenWithProgids"; ValueType: string; ValueName: "QAudioPlayer.MediaFile"; ValueData: ""; Flags: uninsdeletevalue; Tasks: registerdefault
Root: HKA; Subkey: "Software\Classes\.wma\OpenWithProgids"; ValueType: string; ValueName: "QAudioPlayer.MediaFile"; ValueData: ""; Flags: uninsdeletevalue; Tasks: registerdefault

; "Open with" entries for video formats
Root: HKA; Subkey: "Software\Classes\.mp4\OpenWithProgids"; ValueType: string; ValueName: "QAudioPlayer.MediaFile"; ValueData: ""; Flags: uninsdeletevalue; Tasks: registerdefault
Root: HKA; Subkey: "Software\Classes\.mov\OpenWithProgids"; ValueType: string; ValueName: "QAudioPlayer.MediaFile"; ValueData: ""; Flags: uninsdeletevalue; Tasks: registerdefault
Root: HKA; Subkey: "Software\Classes\.m4v\OpenWithProgids"; ValueType: string; ValueName: "QAudioPlayer.MediaFile"; ValueData: ""; Flags: uninsdeletevalue; Tasks: registerdefault
Root: HKA; Subkey: "Software\Classes\.avi\OpenWithProgids"; ValueType: string; ValueName: "QAudioPlayer.MediaFile"; ValueData: ""; Flags: uninsdeletevalue; Tasks: registerdefault
Root: HKA; Subkey: "Software\Classes\.mkv\OpenWithProgids"; ValueType: string; ValueName: "QAudioPlayer.MediaFile"; ValueData: ""; Flags: uninsdeletevalue; Tasks: registerdefault
Root: HKA; Subkey: "Software\Classes\.webm\OpenWithProgids"; ValueType: string; ValueName: "QAudioPlayer.MediaFile"; ValueData: ""; Flags: uninsdeletevalue; Tasks: registerdefault
Root: HKA; Subkey: "Software\Classes\.wmv\OpenWithProgids"; ValueType: string; ValueName: "QAudioPlayer.MediaFile"; ValueData: ""; Flags: uninsdeletevalue; Tasks: registerdefault
Root: HKA; Subkey: "Software\Classes\.flv\OpenWithProgids"; ValueType: string; ValueName: "QAudioPlayer.MediaFile"; ValueData: ""; Flags: uninsdeletevalue; Tasks: registerdefault

; Register the app in the Default Apps system (per-user)
Root: HKA; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "QAudioPlayer"; ValueData: "Software\QAudioPlayer\Capabilities"; Flags: uninsdeletevalue; Tasks: registerdefault
Root: HKA; Subkey: "Software\QAudioPlayer\Capabilities"; ValueType: string; ValueName: "ApplicationName"; ValueData: "QAudioPlayer"; Flags: uninsdeletekey; Tasks: registerdefault
Root: HKA; Subkey: "Software\QAudioPlayer\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "A keyboard-first, accessible media player with QuickTime-style JKL controls."; Tasks: registerdefault

; File associations under Capabilities
Root: HKA; Subkey: "Software\QAudioPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mp3"; ValueData: "QAudioPlayer.MediaFile"; Tasks: registerdefault
Root: HKA; Subkey: "Software\QAudioPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".wav"; ValueData: "QAudioPlayer.MediaFile"; Tasks: registerdefault
Root: HKA; Subkey: "Software\QAudioPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".m4a"; ValueData: "QAudioPlayer.MediaFile"; Tasks: registerdefault
Root: HKA; Subkey: "Software\QAudioPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mp4"; ValueData: "QAudioPlayer.MediaFile"; Tasks: registerdefault
Root: HKA; Subkey: "Software\QAudioPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mov"; ValueData: "QAudioPlayer.MediaFile"; Tasks: registerdefault
Root: HKA; Subkey: "Software\QAudioPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".flac"; ValueData: "QAudioPlayer.MediaFile"; Tasks: registerdefault
Root: HKA; Subkey: "Software\QAudioPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mkv"; ValueData: "QAudioPlayer.MediaFile"; Tasks: registerdefault
Root: HKA; Subkey: "Software\QAudioPlayer\Capabilities\FileAssociations"; ValueType: string; ValueName: ".avi"; ValueData: "QAudioPlayer.MediaFile"; Tasks: registerdefault

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
Filename: "ms-settings:defaultapps"; Description: "Open Windows Default Apps settings to set as default"; Flags: nowait postinstall skipifsilent shellexec

[Code]
function IsVLCInstalled(): Boolean;
begin
  Result := RegKeyExists(HKEY_LOCAL_MACHINE,
    'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\VLC media player');
  if not Result then
    Result := RegKeyExists(HKEY_CURRENT_USER,
      'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\VLC media player');
  if not Result then
    Result := RegKeyExists(HKEY_LOCAL_MACHINE,
      'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\VLC media player');
end;

function InitializeSetup(): Boolean;
var
  ErrorCode: Integer;
  Message: String;
begin
  Result := True;
  if not IsVLCInstalled() then begin
    Message :=
      'QAudioPlayer requires VLC media player (64-bit) to be installed.' + #13#10 +
      'VLC does not appear to be installed on this computer.' + #13#10 + #13#10 +
      'Would you like to open VLC''s download page now?' + #13#10 + #13#10 +
      'You may continue with the installation and install VLC afterwards, but' + #13#10 +
      'QAudioPlayer will not play any files until VLC is installed.' + #13#10 + #13#10 +
      'Click Yes to open VLC''s download page, or No to continue without it.';

    if MsgBox(Message, mbConfirmation, MB_YESNO) = IDYES then
    begin
      ShellExec('open', 'https://www.videolan.org/vlc/download-windows.html',
               '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
    end;
  end;
end;
