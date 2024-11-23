#define MyAppName "Alieraser"
#define MyAppVersion "1.0"
#define MyAppPublisher "Tu Empresa"
#define MyAppExeName "Alieraser.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-G7H8-I9J0-K1L2M3N4O5P6}}  ; Reemplaza esto con un GUID único
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=Alieraser_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=iconos\app_icon.ico

; Configuración de permisos de administrador
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
AlwaysRestart=yes

; Logging y configuración adicional
SetupLogging=yes
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\Alieraser\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\Alieraser\images_history\*"; DestDir: "{app}\images_history"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Configurar permisos de carpeta principal
Filename: "cmd.exe"; Parameters: "/c icacls ""{app}"" /grant *S-1-1-0:(OI)(CI)F /T"; \
    Flags: runhidden runascurrentuser; StatusMsg: "Configurando permisos..."

; Configurar permisos específicos para images_history
Filename: "cmd.exe"; Parameters: "/c icacls ""{app}\images_history"" /grant *S-1-1-0:(OI)(CI)F /T"; \
    Flags: runhidden runascurrentuser; StatusMsg: "Configurando permisos de images_history..."

; Ejecutar la aplicación
Filename: "{app}\{#MyAppExeName}"; \
    Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; \
    Flags: nowait postinstall skipifsilent

[Dirs]
Name: "{app}\images_history"; Permissions: users-modify authusers-modify

[UninstallDelete]
Type: filesandordirs; Name: "{app}\images_history"