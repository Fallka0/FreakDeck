#include <Keypad.h>
#include <TFT_eSPI.h>

TFT_eSPI tft = TFT_eSPI();

#define TFT_BL 4
#define TFT_BACKLIGHT_ON HIGH

const byte ROWS = 4;
const byte COLS = 3;

char keys[ROWS][COLS] = {
  { '1', '2', '3' },
  { '4', '5', '6' },
  { '7', '8', '9' },
  { '*', '0', '#' }
};

byte rowPins[ROWS] = {21, 27, 26, 22};
byte colPins[COLS] = {33, 32, 25};

Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

int currentVolume = 50;
bool isMuted = false;
String hostName = "Host";
String nowPlaying = "Nichts aktiv";
String serialLine = "";

const unsigned long VOLUME_POPUP_MS = 2500;
unsigned long volumeOverlayUntil = 0;
bool lastOverlayVisible = false;

bool isVolumeOverlayVisible() {
  return millis() < volumeOverlayUntil;
}

void showVolumeOverlay() {
  volumeOverlayUntil = millis() + VOLUME_POPUP_MS;
}

void drawCard(int x, int y, int w, int h, uint16_t borderColor) {
  tft.fillRoundRect(x, y, w, h, 8, TFT_BLACK);
  tft.drawRoundRect(x, y, w, h, 8, borderColor);
}

void drawVolumeBar(int x, int y, int w, int h, int percent) {
  percent = constrain(percent, 0, 100);

  tft.drawRoundRect(x, y, w, h, 6, TFT_WHITE);
  tft.fillRoundRect(x + 2, y + 2, w - 4, h - 4, 4, TFT_BLACK);

  int fillW = ((w - 4) * percent) / 100;
  if (fillW > 0) {
    uint16_t color = TFT_GREEN;
    if (percent < 30) color = TFT_RED;
    else if (percent < 60) color = TFT_YELLOW;
    tft.fillRoundRect(x + 2, y + 2, fillW, h - 4, 4, color);
  }
}

String normalizeSpaces(String text) {
  String out = "";
  bool prevSpace = false;

  for (size_t i = 0; i < text.length(); i++) {
    char c = text[i];
    bool isSpace = (c == ' ' || c == '\t' || c == '\r' || c == '\n');

    if (isSpace) {
      if (!prevSpace) {
        out += ' ';
        prevSpace = true;
      }
    } else {
      out += c;
      prevSpace = false;
    }
  }

  out.trim();
  return out;
}

String addEllipsis(String text, int maxLen) {
  text.trim();
  if ((int)text.length() <= maxLen) return text;
  if (maxLen <= 3) return text.substring(0, maxLen);
  return text.substring(0, maxLen - 3) + "...";
}

void splitIntoTwoLines(String text, int maxLine1, int maxLine2, String &line1, String &line2) {
  text = normalizeSpaces(text);

  if (text.length() == 0) {
    line1 = "Nichts aktiv";
    line2 = "";
    return;
  }

  if ((int)text.length() <= maxLine1) {
    line1 = text;
    line2 = "";
    return;
  }

  int splitPos = -1;
  int searchMax = min((int)text.length() - 1, maxLine1);

  for (int i = searchMax; i >= 0; i--) {
    if (text[i] == ' ') {
      splitPos = i;
      break;
    }
  }

  if (splitPos == -1) {
    splitPos = maxLine1;
  }

  line1 = text.substring(0, splitPos);
  line1.trim();

  String remaining = text.substring(splitPos);
  remaining.trim();

  if ((int)remaining.length() <= maxLine2) {
    line2 = remaining;
  } else {
    int splitPos2 = -1;
    int searchMax2 = min((int)remaining.length() - 1, maxLine2);

    for (int i = searchMax2; i >= 0; i--) {
      if (remaining[i] == ' ') {
        splitPos2 = i;
        break;
      }
    }

    if (splitPos2 == -1) {
      line2 = addEllipsis(remaining, maxLine2);
    } else {
      String candidate = remaining.substring(0, splitPos2);
      candidate.trim();

      String leftover = remaining.substring(splitPos2);
      leftover.trim();

      if (leftover.length() > 0) {
        line2 = addEllipsis(candidate, maxLine2);
      } else {
        line2 = candidate;
      }
    }
  }
}

void drawNowPlayingCard() {
  drawCard(8, 34, 224, 58, TFT_DARKGREY);

  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(TFT_YELLOW, TFT_BLACK);
  tft.drawString("Now Playing", 16, 40, 2);

  String line1, line2;
  splitIntoTwoLines(nowPlaying, 30, 30, line1, line2);

  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.drawString(line1, 16, 58, 2);

  if (line2.length() > 0) {
    tft.drawString(line2, 16, 72, 2);
  }
}

void drawVolumeOverlay() {
  drawCard(8, 96, 224, 26, TFT_DARKGREY);

  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(TFT_GREEN, TFT_BLACK);
  tft.drawString("Volume", 16, 101, 2);

  char volText[12];
  if (isMuted) {
    snprintf(volText, sizeof(volText), "MUTE");
  } else {
    snprintf(volText, sizeof(volText), "%d%%", currentVolume);
  }

  tft.setTextDatum(TR_DATUM);
  tft.setTextColor(isMuted ? TFT_RED : TFT_WHITE, TFT_BLACK);
  tft.drawString(volText, 220, 101, 2);

  if (isMuted) {
    drawVolumeBar(76, 104, 96, 10, 0);
  } else {
    drawVolumeBar(76, 104, 96, 10, currentVolume);
  }
}

void renderUI() {
  tft.fillScreen(TFT_BLACK);

  tft.setTextDatum(TL_DATUM);
  tft.setTextColor(TFT_CYAN, TFT_BLACK);
  tft.drawString("FreakDeck", 10, 8, 4);

  tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
  tft.drawString(hostName, 170, 12, 2);

  drawNowPlayingCard();

  if (isVolumeOverlayVisible()) {
    drawVolumeOverlay();
  }

  tft.setTextColor(TFT_DARKGREY, TFT_BLACK);
  tft.drawString("1-9 Aktionen   *-/0 mute/#+", 12, 124, 1);
}

void sendEventForKey(char key) {
  switch (key) {
    case '1': Serial.println("BTN_1"); break;
    case '2': Serial.println("BTN_2"); break;
    case '3': Serial.println("BTN_3"); break;
    case '4': Serial.println("BTN_4"); break;
    case '5': Serial.println("BTN_5"); break;
    case '6': Serial.println("BTN_6"); break;
    case '7': Serial.println("BTN_7"); break;
    case '8': Serial.println("BTN_8"); break;
    case '9': Serial.println("BTN_9"); break;

    case '*':
      Serial.println("VOL_DOWN");
      showVolumeOverlay();
      break;

    case '0':
      Serial.println("MUTE_TOGGLE");
      showVolumeOverlay();
      break;

    case '#':
      Serial.println("VOL_UP");
      showVolumeOverlay();
      break;
  }

  renderUI();
}

void processCommand(String cmd) {
  cmd.trim();
  if (cmd.length() == 0) return;

  Serial.println("ACK:" + cmd);

  if (cmd.startsWith("SET_VOL:")) {
    int value = cmd.substring(8).toInt();
    currentVolume = constrain(value, 0, 100);
    renderUI();
  }
  else if (cmd.startsWith("SET_MUTE:")) {
    int value = cmd.substring(9).toInt();
    isMuted = (value != 0);
    renderUI();
  }
  else if (cmd.startsWith("STATUS:")) {
    hostName = cmd.substring(7);
    renderUI();
  }
  else if (cmd.startsWith("NOW_PLAYING:")) {
    nowPlaying = cmd.substring(12);
    renderUI();
  }
}

void readSerialCommands() {
  while (Serial.available()) {
    char c = (char)Serial.read();

    if (c == '\n') {
      processCommand(serialLine);
      serialLine = "";
    } else if (c != '\r') {
      serialLine += c;
      if (serialLine.length() > 140) {
        serialLine = "";
      }
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(300);

  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, TFT_BACKLIGHT_ON);

  tft.init();
  tft.setRotation(1);
  renderUI();

  Serial.println("READY");
}

void loop() {
  readSerialCommands();

  bool overlayVisible = isVolumeOverlayVisible();
  if (overlayVisible != lastOverlayVisible) {
    lastOverlayVisible = overlayVisible;
    renderUI();
  }

  char key = keypad.getKey();
  if (key) {
    sendEventForKey(key);
    delay(120);
  }
}