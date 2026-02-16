# build_standalone_bundle.ps1
$VenvSource = "Z:\Ruta\Al\Tu\.venv"  # <--- Tu venv de red
$BundleDir = "BuMPeR_Standalone"

Write-Host "--- Iniciando Empaquetado Totalmente Autónomo ---" -ForegroundColor Cyan

# 1. Crear estructura limpia
if (Test-Path $BundleDir) { Remove-Item -Recurse -Force $BundleDir }
New-Item -ItemType Directory -Force -Path "$BundleDir\runtime", "$BundleDir\app", "$BundleDir\data"

# 2. Leer pyvenv.cfg original para localizar el Python base (home)
$CfgPath = "$VenvSource\pyvenv.cfg"
if (-not (Test-Path $CfgPath)) { throw "No se encuentra pyvenv.cfg en el origen." }

$CfgContent = Get-Content $CfgPath
$HomeLine = $CfgContent | Where-Object { $_ -match "^home\s*=" }
$OriginalHome = ($HomeLine -split "=")[1].Trim()

Write-Host "Localizado Python Base en: $OriginalHome" -ForegroundColor Yellow

# 3. COPIAR BINARIOS BASE (Archivos C, DLLs y Exe original)
# Esto es lo que permite que funcione sin Python instalado en el sistema
Write-Host "Copiando binarios base (incluyendo C-Runtime)..."
$BasePythonDir = "$BundleDir\runtime\python_base"
New-Item -ItemType Directory -Force -Path $BasePythonDir
Copy-Item -Path "$OriginalHome\*" -Destination $BasePythonDir -Force -Exclude "Lib","Doc","include"

# 4. COPIAR CONTENIDO DEL VENV
Write-Host "Copiando entorno virtual..."
Copy-Item -Path "$VenvSource\Scripts" -Destination "$BundleDir\runtime\Scripts" -Recurse -Force
Copy-Item -Path "$VenvSource\Lib" -Destination "$BundleDir\runtime\Lib" -Recurse -Force

# 5. MODIFICAR pyvenv.cfg POST-INSTALACIÓN
# Aquí cambiamos la ruta 'home' para que apunte a nuestra carpeta local
Write-Host "Reconfigurando pyvenv.cfg para portabilidad..."
$NewCfgPath = "$BundleDir\runtime\pyvenv.cfg"
$NewHome = "python_base" # Ruta relativa

$NewCfgContent = @()
foreach ($line in $CfgContent) {
    if ($line -match "^home\s*=") {
        $NewCfgContent += "home = $NewHome"
    } else {
        $NewCfgContent += $line
    }
}
$NewCfgContent | Out-File -FilePath $NewCfgPath -Encoding utf8

# 6. Copiar aplicación
Copy-Item -Path ".\src\*" -Destination "$BundleDir\app" -Recurse -Force
Copy-Item -Path ".\main.py" -Destination "$BundleDir\app" -Force

# 7. Crear el lanzador .bat
$BatContent = @"
@echo off
setlocal
:: %~dp0 es la clave para la ruta relativa
set "BASE_DIR=%~dp0"
set "PY_EXE=%BASE_DIR%runtime\Scripts\python.exe"
set "APP_MAIN=%BASE_DIR%app\main.py"

:: Ejecutar pasándole los argumentos de la CLI
"%PY_EXE%" "%APP_MAIN%" %*
"@
$BatContent | Out-File -FilePath "$BundleDir\BuMPeR_App.bat" -Encoding ascii

Write-Host "--- Bundle Autónomo creado en: $BundleDir ---" -ForegroundColor Green
