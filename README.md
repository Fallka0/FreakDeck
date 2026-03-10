# FreakDeck

FreakDeck is a USB-connected macro pad built around a LilyGO T-Display keyboard module and a desktop companion app.

It lets you:
- launch websites, apps, and folders with physical buttons
- control system volume with dedicated hardware keys
- toggle mute directly from the device
- show live status information on the built-in screen
- display the current “Now Playing” title on the device screen

## Features

### Hardware
- LilyGO T-Display keyboard module
- 3x4 key matrix
- built-in screen for status and media info
- USB serial connection to the computer

### Button layout
- `1` to `9`: user-configurable actions
- `*`: volume down
- `0`: mute / unmute
- `#`: volume up

### Companion app
- Windows desktop app built from Python
- serial auto-detection for FreakDeck
- setup/config GUI for button mappings
- supports:
  - URLs
  - apps / executables
  - folders / paths
- live volume sync
- live now-playing sync

### Screen UI
- shows current “Now Playing” text
- shows a temporary volume overlay after volume or mute actions
- designed to maximize space for media info instead of always showing the volume bar

## How it works

The FreakDeck hardware sends button events over USB serial to the desktop app.

The desktop app then:
- performs the mapped action for `BTN_1` to `BTN_9`
- changes system volume for `VOL_UP`, `VOL_DOWN`, and `MUTE_TOGGLE`
- sends the real system volume and mute state back to the device
- sends “Now Playing” text back to the device screen

This keeps the screen display in sync with the actual OS state.

## Supported platforms

### Windows
- app launching via `.exe`
- folder opening via Explorer
- volume and mute via Windows audio APIs
- “Now Playing” based on the active window title, useful for browser tabs like YouTube

### macOS
- app/folder opening via `open`
- volume and mute via AppleScript
- “Now Playing” via AppleScript for apps like Spotify and Music

## Installation

### End users
Use the packaged installer:
- run `FreakDeckInstaller.exe`
- install the app
- launch FreakDeck from the shortcut
- connect the device via USB

### Development build
If running from source, the project currently uses Python with:
- `pyserial`
- `pycaw` (Windows)
- `PyGetWindow` (Windows)

Example install:

```bash
python -m pip install pyserial pycaw PyGetWindow
```

## Packaging

The desktop app is packaged with:
- **PyInstaller** for a standalone Windows app
- **Inno Setup** for a normal Windows installer

Typical output:
- app: `dist/FreakDeck/FreakDeck.exe`
- installer: `Output/FreakDeckInstaller.exe`

## Setup flow

Current setup is designed around a companion GUI with:
1. device detection
2. platform selection
3. key assignment
4. live testing
5. saving configuration

Planned direction:
- simpler first-run onboarding
- customer-friendly wizard flow
- optional integrated firmware install/update
- easier preset-based setup

## Configuration

`BTN_1` to `BTN_9` can be mapped to:
- `url`
- `app`
- `path`

Examples:
- `https://www.youtube.com`
- `C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe`
- `C:\\Users\\Name\\Documents`

## Current limitations

- Windows “Now Playing” is based on the active window title, not a universal media session API
- the current configuration is stored on the computer, not yet on the device
- automatic firmware flashing is not yet integrated into the app
- some users may still need a USB serial driver depending on the board’s USB/UART chip

## Recommended customer experience roadmap

Short term:
- polished desktop installer
- simpler setup wizard
- presets for common users
- clearer driver/setup guidance

Next steps:
- built-in firmware updater
- optional device-side profile storage
- more polished onboarding and recovery tools
- richer “Now Playing” support

## Project structure

Example high-level layout:

```text
GUI.py
build_app.bat
build_installer.bat
installer.iss
webpad_config.json
README.md
```

## Troubleshooting

### Device not detected
- try another USB cable
- close Arduino IDE / Serial Monitor / any tool using the COM port
- reconnect the device
- rescan ports in the app

### Volume works but screen does not update
- make sure the companion app is connected to the same serial port
- verify the device firmware supports `SET_VOL`, `SET_MUTE`, and `NOW_PLAYING`

### “Now Playing” not showing on Windows
- make sure the media/browser window is the active window
- install `PyGetWindow`
- restart the app after installing dependencies

## License / usage

Add your preferred license and commercial terms here.

---

If you plan to sell FreakDeck, this README should evolve into two versions:
- a **developer README** for building and maintaining the project
- a **customer quick-start guide** for installation and everyday use
