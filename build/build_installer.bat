@echo off
cd /d %~dp0

set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

if not exist %ISCC% (
  echo Inno Setup compiler not found at:
  echo %ISCC%
  pause
  exit /b 1
)

%ISCC% installer.iss

echo.
echo Installer build finished.
echo Output file should be in:
echo Output\FreakDeckInstaller.exe
pause