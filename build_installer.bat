@echo off
cd /d %~dp0

set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

if not exist %ISCC% (
  echo Inno Setup compiler not found.
  pause
  exit /b 1
)

%ISCC% src\install.iss

echo.
echo Installer build finished.
echo Output: Output\FreakDeckInstaller.exe
pause