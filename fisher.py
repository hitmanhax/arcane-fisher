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
import numpy as np
import pyautogui
import time
import random
import threading
from pynput import keyboard as kb

# ── Failsafe: move mouse to top-left corner to crash pyautogui intentionally ──
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0  # remove default delay between pyautogui calls

# ─────────────────────────── Configuration ────────────────────────────────────

CAST_KEY = 'e'          # Key that casts the fishing rod
CLICK_INTERVAL = 0.04   # Seconds between clicks while reeling (~25 cps)
RECAST_DELAY = (0.2, 0.4)   # Random delay (seconds) before recasting after catch

# How many red pixels must be present to count as a "bite"
# Increase if you're getting false positives, lower if bites are missed
MIN_RED_PIXELS = 30

# Detection region as fraction of screen
# Covers center strip where the ! box appears above the character's head
REGION_LEFT_FRAC   = 0.38
REGION_TOP_FRAC    = 0.15
REGION_WIDTH_FRAC  = 0.24
REGION_HEIGHT_FRAC = 0.45

# Pure RGB thresholds for the bright red ! mark (in BGRA channel order)
# R > 180, G < 80, B < 80  →  vivid red
RED_R_MIN = 180
RED_G_MAX = 80
RED_B_MAX = 80

# ──────────────────────────────────────────────────────────────────────────────


class ArcaneOdysseyFisher:
    def __init__(self):
        self.running = False
        self.state = "IDLE"
        self._thread = None
        self.sct = None  # created inside the worker thread

        # Read screen dimensions on the main thread (short-lived instance)
        with mss.mss() as tmp:
            mon = tmp.monitors[1]
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
        raw = self.sct.grab(self.region)
        # mss returns BGRA — channels: 0=B, 1=G, 2=R, 3=A
        img = np.frombuffer(raw.bgra, dtype=np.uint8).reshape(raw.height, raw.width, 4)
        red_mask = (
            (img[:, :, 2] >= RED_R_MIN) &  # R high
            (img[:, :, 1] <= RED_G_MAX) &  # G low
            (img[:, :, 0] <= RED_B_MAX)    # B low
        )
        return int(np.count_nonzero(red_mask)) >= MIN_RED_PIXELS

    # ── Game actions ──────────────────────────────────────────────────────────

    def _cast(self):
        pyautogui.press(CAST_KEY)
        print("[CAST]   Rod cast — waiting for bite...")

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _loop(self):
        # Create mss instance on this thread — Windows handles are thread-local
        self.sct = mss.mss()
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
