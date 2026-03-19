"""
Arcane Odyssey Auto Fisher
--------------------------
Watches the screen for the red exclamation mark (!) that appears
above your character's head when a fish bites, then auto-reels.

Controls:
  F8  - Start / Stop
  F9  - Emergency stop (also moves mouse to top-left to trigger failsafe)

Setup:
  1. Equip your fishing rod in Roblox
  2. Run this script
  3. Cast your rod manually once (press E in-game)
  4. Press F8 to start the bot
"""

import mss
import cv2
import numpy as np
import pyautogui
import time
import random
import threading
from threading import Lock
from pynput import keyboard as kb

# ── Failsafe: move mouse to top-left corner to crash pyautogui intentionally ──
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0  # remove default delay between pyautogui calls

# ─────────────────────────── Configuration ────────────────────────────────────

CAST_KEY = 'e'          # Key that casts the fishing rod
CLICK_INTERVAL = 0.04   # Seconds between clicks while reeling (~25 cps)
RECAST_DELAY = (0.2, 0.4)   # Random delay (seconds) before recasting after catch

# How many red pixels must be present to count as a "bite"
# Increase this if you're getting false positives, lower it if bites are missed
MIN_RED_PIXELS = 40

# Detection region as fraction of screen (tweak if your character is off-center)
# Default: center third of screen width, middle vertical band
REGION_LEFT_FRAC   = 0.33
REGION_TOP_FRAC    = 0.20
REGION_WIDTH_FRAC  = 0.34
REGION_HEIGHT_FRAC = 0.50

# Red color bounds in HSV (OpenCV uses H: 0-179, S: 0-255, V: 0-255)
# Two ranges needed because red wraps around the hue wheel
RED_RANGES = [
    (np.array([0,   160, 160]), np.array([8,  255, 255])),
    (np.array([172, 160, 160]), np.array([179, 255, 255])),
]

# ──────────────────────────────────────────────────────────────────────────────


class ArcaneOdysseyFisher:
    def __init__(self):
        self.running = False
        self.state = "IDLE"
        self._thread = None
        self.sct = mss.mss()
        self._sct_lock = Lock()

        mon = self.sct.monitors[1]  # primary monitor
        sw, sh = mon["width"], mon["height"]

        self.region = {
            "top":    int(sh * REGION_TOP_FRAC),
            "left":   int(sw * REGION_LEFT_FRAC),
            "width":  int(sw * REGION_WIDTH_FRAC),
            "height": int(sh * REGION_HEIGHT_FRAC),
        }

        print(f"  Screen      : {sw}x{sh}")
        print(f"  Watch region: {self.region}")

    # ── Screen detection ──────────────────────────────────────────────────────

    def _exclamation_visible(self) -> bool:
        """Return True when enough red pixels are found in the watch region."""
        with self._sct_lock:
            raw = self.sct.grab(self.region)
            img = np.frombuffer(raw.bgra, dtype=np.uint8).reshape(raw.height, raw.width, 4)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGRA2HSV)

        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for lo, hi in RED_RANGES:
            mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lo, hi))

        return int(cv2.countNonZero(mask)) >= MIN_RED_PIXELS

    # ── Game actions ──────────────────────────────────────────────────────────

    def _cast(self):
        pyautogui.press(CAST_KEY)
        print("[CAST]   Rod cast — waiting for bite...")

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _loop(self):
        time.sleep(1.0)  # brief pause so you can alt-tab into Roblox
        self._cast()
        self.state = "WAITING"

        while self.running:
            if self.state == "WAITING":
                if self._exclamation_visible():
                    print("[BITE!]  Reeling...")
                    self.state = "REELING"

            elif self.state == "REELING":
                if self._exclamation_visible():
                    pyautogui.click()
                    time.sleep(CLICK_INTERVAL)
                else:
                    print("[CAUGHT] Fish reeled in!")
                    delay = random.uniform(*RECAST_DELAY)
                    time.sleep(delay)
                    self._cast()
                    self.state = "WAITING"

            time.sleep(0.016)  # ~60 fps polling

        print("[STOPPED]")

    # ── Public control ────────────────────────────────────────────────────────

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[START]  Fisher running. Press F8 to stop.")

    def stop(self):
        self.running = False
        self.state = "IDLE"


# ── Hotkey listener ───────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("  Arcane Odyssey Auto Fisher")
    print("=" * 50)
    print("  F8  - Start / Stop")
    print("  F9  - Emergency stop")
    print()
    print("  Make sure:")
    print("  1. Roblox is running and focused")
    print("  2. Fishing rod is equipped")
    print("  3. Cast the rod once manually, then press F8")
    print("=" * 50)
    print()

    fisher = ArcaneOdysseyFisher()

    def on_press(key):
        if key == kb.Key.f8:
            if not fisher.running:
                fisher.start()
            else:
                fisher.stop()
        elif key == kb.Key.f9:
            fisher.stop()
            pyautogui.moveTo(0, 0)  # trigger failsafe as extra safety

    with kb.Listener(on_press=on_press) as listener:
        listener.join()


if __name__ == "__main__":
    main()
