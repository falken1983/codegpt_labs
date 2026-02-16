@echo off
setlocal enabledelayedexpansion

:: --- CONFIGURACION ---
set "VENV_SOURCE=Z:\Ruta\Al\Tu\.venv"
set "BUNDLE_DIR=BuMPeR_Standalone"

echo -------------------------------------------------------
echo Iniciando Empaquetado Autónomo (Modo CMD)
echo -------------------------------------------------------

:: 1. Limpieza y creación de carpetas
if exist "%BUNDLE_DIR%" rd /s /q "%BUNDLE_DIR%"
mkdir "%BUNDLE_DIR%\runtime\python_base"
mkdir "%BUNDLE_DIR%\runtime\Scripts"
mkdir "%BUNDLE_DIR%\runtime\Lib"
mkdir "%BUNDLE_DIR%\app"
mkdir "%BUNDLE_DIR%\data"

:: 2. Extraer la ruta 'home' del pyvenv.cfg original
echo Localizando Python base...
set "ORIGINAL_HOME="
for /f "tokens=2 delims==" %%A in ('findstr /i "home =" "%VENV_SOURCE%\pyvenv.cfg"') do (
    set "RAW_HOME=%%A"
    :: Quitar el espacio inicial si existe
    set "ORIGINAL_HOME=!RAW_HOME:~1!"
)

if "!ORIGINAL_HOME!"=="" (
    echo [ERROR] No se pudo encontrar la linea 'home' en pyvenv.cfg
    pause
    exit /b 1
)

echo Python base detectado en: !ORIGINAL_HOME!

:: 3. Copiar Binarios Base (Archivos C, DLLs, etc.)
echo Copiando archivos del sistema (C-Runtime y DLLs)...
:: Copiamos los archivos de la raiz de Python (exe, dll) pero ignoramos carpetas grandes
xcopy "!ORIGINAL_HOME!\*.dll" "%BUNDLE_DIR%\runtime\python_base\" /y
xcopy "!ORIGINAL_HOME!\*.exe" "%BUNDLE_DIR%\runtime\python_base\" /y

:: 4. Copiar contenido del VENV
echo Copiando Scripts y Librerias del entorno virtual...
xcopy "%VENV_SOURCE%\Scripts\*.*" "%BUNDLE_DIR%\runtime\Scripts\" /e /i /y
xcopy "%VENV_SOURCE%\Lib\*.*" "%BUNDLE_DIR%\runtime\Lib\" /e /i /y

:: 5. Reconfigurar pyvenv.cfg para que sea relativo
echo Generando nuevo pyvenv.cfg portable...
(
    echo home = python_base
    echo include-system-site-packages = false
    echo version = 3.11.5
    echo executable = python_base\python.exe
    echo command = python_base\python.exe -m venv ..\runtime
) > "%BUNDLE_DIR%\runtime\pyvenv.cfg"

:: 6. Copiar aplicación
echo Copiando codigo fuente...
if exist "src" xcopy "src\*.*" "%BUNDLE_DIR%\app\src\" /e /i /y
copy "main.py" "%BUNDLE_DIR%\app\" /y

:: 7. Crear el lanzador final BuMPeR_App.bat
echo Creando lanzador de usuario...
(
    echo @echo off
    echo setlocal
    echo set "BASE_DIR=%%~dp0"
    echo set "PY_EXE=%%BASE_DIR%%runtime\Scripts\python.exe"
    echo set "APP_MAIN=%%BASE_DIR%%app\main.py"
    echo "%%PY_EXE%%" "%%APP_MAIN%%" %%*
) > "%BUNDLE_DIR%\BuMPeR_App.bat"

echo -------------------------------------------------------
echo PROCESO COMPLETADO
echo El paquete esta listo en: %BUNDLE_DIR%
echo -------------------------------------------------------
pause