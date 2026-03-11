@echo off
cd /d %~dp0

python -m pip install --upgrade pip pyinstaller
python -m PyInstaller --noconfirm --clean --windowed --name FreakDeck GUI.py

echo.
echo Build finished.
echo Output: dist\FreakDeck\FreakDeck.exe
pause