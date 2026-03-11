# FreakDeck (Windows)

FreakDeck is the desktop companion app for the FreakDeck hardware macro pad.

It lets you:
- map hardware buttons to websites, apps, and folders
- control system volume from the device
- mute / unmute directly from hardware
- sync live status back to the FreakDeck screen
- display the current “Now Playing” title on the device

---

## Features

### Hardware button layout
- `1` to `9` → user-configurable actions
- `*` → volume down
- `0` → mute / unmute
- `#` → volume up

### Desktop app
- serial port auto-detection
- config save / load
- launch URLs
- launch `.exe` apps
- open folders / paths
- live Windows volume sync
- mute toggle
- now-playing sync
- custom app icon
- packaged `.exe`
- packaged Windows installer

---

# Installation Guide (Windows)

This section is for normal users.

## Requirements
- Windows PC
- FreakDeck device
- USB data cable
- `FreakDeckInstaller.exe`

## Install the app
1. Download `FreakDeckInstaller.exe`
2. Double-click it
3. Follow the installer steps
4. Launch **FreakDeck** from the desktop or Start Menu

## Connect the device
1. Plug the FreakDeck into your PC using USB
2. Open the FreakDeck app
3. Select the serial port if needed
4. Click **Connect**

## Configure buttons
Inside the app, `BTN_1` to `BTN_9` can be mapped to:
- `url`
- `app`
- `path`

Examples:
- `https://www.youtube.com`
- `C:\Program Files\Google\Chrome\Application\chrome.exe`
- `C:\Users\YourName\Documents`

## Save configuration
After assigning your buttons:
1. Click **Save config**
2. Your configuration will be stored locally in `webpad_config.json`

---

# How it works

The FreakDeck hardware sends button events to the desktop app over USB serial.

The desktop app then:
- executes the mapped action for `BTN_1` to `BTN_9`
- changes system volume for `VOL_UP`, `VOL_DOWN`, and `MUTE_TOGGLE`
- reads the current system audio state
- sends volume, mute state, and now-playing text back to the device

This keeps the PC and FreakDeck display in sync.

---

# Using the App

## Device section
Use this area to:
- select the serial port
- choose platform
- rescan ports
- connect / disconnect
- load config
- save config

## Button mappings
Map each button to:
- a URL
- an app
- a folder path

Use:
- **Browse** to pick files/folders
- **Test** to test a mapping before using the device
- **Starter preset** for a quick default setup
- **Clear all** to reset mappings

## Live status
The right side of the app shows:
- device connection status
- current volume
- now playing title
- live log output

---

# Troubleshooting

## Device not detected
Try this:
1. unplug and reconnect the USB cable
2. try another USB data cable
3. close Arduino IDE / Serial Monitor / any serial tools
4. click **Rescan**
5. reopen the app

## Serial port is busy
Close anything that may already be using the device:
- Arduino IDE
- Serial Monitor
- another FreakDeck instance
- serial terminal tools

## Volume works but screen does not update
Make sure:
- the app is connected to the correct serial port
- the device firmware supports:
  - `SET_VOL`
  - `SET_MUTE`
  - `NOW_PLAYING`

## Now Playing is empty
On Windows, now-playing is based on the **active window title**.

That means it works best when:
- the media tab/window is focused
- YouTube or another media source is the active browser tab


