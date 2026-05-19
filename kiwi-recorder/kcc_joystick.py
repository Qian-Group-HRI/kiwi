import ctypes
import ctypes.wintypes as wt
import json
import logging
import os
import threading
import time

logger = logging.getLogger("kcc.joystick")

winmm = ctypes.WinDLL('winmm')

class JOYINFOEX(ctypes.Structure):
    _fields_ = [
        ('dwSize', wt.DWORD), ('dwFlags', wt.DWORD),
        ('dwXpos', wt.DWORD), ('dwYpos', wt.DWORD),
        ('dwZpos', wt.DWORD), ('dwRpos', wt.DWORD),
        ('dwUpos', wt.DWORD), ('dwVpos', wt.DWORD),
        ('dwButtons', wt.DWORD), ('dwButtonNumber', wt.DWORD),
        ('dwPOV', wt.DWORD),
        ('dwReserved1', wt.DWORD), ('dwReserved2', wt.DWORD),
    ]

def read_joystick(joy_id=0):
    info = JOYINFOEX()
    info.dwSize = ctypes.sizeof(JOYINFOEX)
    info.dwFlags = 0xFF
    if winmm.joyGetPosEx(joy_id, ctypes.byref(info)) != 0:
        return None
    n = lambda v: (v - 32767) / 32767
    return {
        "axes": [n(info.dwXpos), n(info.dwYpos), n(info.dwZpos),
                 n(info.dwRpos), n(info.dwUpos), n(info.dwVpos)],
        "buttons": info.dwButtons,
    }

DEFAULT_MAP = {
    "deadzone": 0.15, "poll_hz": 30,
    "axes": {
        "0": {"neg": "a", "pos": "d", "label": "Strafe L/R"},
        "1": {"neg": "w", "pos": "s", "label": "Forward/Back"},
        "2": {"neg": "z", "pos": "x", "label": "Rotate"},
    },
    "buttons": {}
}

class JoystickMapper:
    def __init__(self, config_path=None):
        self.config_path = config_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "joystick_map.json")
        self.mapping = {}
        self.load_config()
        self._pressed = set()
        self._btn_prev = 0
        self._kb = None
        self._running = False
        self._thread = None
        self._last_state = None

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path) as f:
                    self.mapping = json.load(f)
                return
            except: pass
        self.mapping = dict(DEFAULT_MAP)
        self.save_config()

    def save_config(self):
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.mapping, f, indent=2)
        except: pass

    def get_state(self):
        return self._last_state

    def get_config(self):
        return self.mapping

    def start(self):
        if self._running: return
        try:
            from pynput.keyboard import Controller
            self._kb = Controller()
        except:
            logger.error("pynput not available")
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="kcc-joystick")
        self._thread.start()
        logger.info("Joystick mapper started (pure Python)")

    def stop(self):
        self._running = False
        if self._thread: self._thread.join(timeout=2)
        self._release_all()

    def _release_all(self):
        if self._kb:
            for k in self._pressed:
                try: self._kb.release(k)
                except: pass
        self._pressed.clear()

    def _loop(self):
        interval = 1.0 / max(self.mapping.get("poll_hz", 30), 1)
        while self._running:
            try:
                state = read_joystick(0)
                if state is None:
                    self._release_all()
                    self._last_state = None
                    time.sleep(0.5)
                    continue
                self._last_state = state
                dz = self.mapping.get("deadzone", 0.15)
                axes = state["axes"]
                should = set()
                for idx_s, km in self.mapping.get("axes", {}).items():
                    idx = int(idx_s)
                    if idx >= len(axes): continue
                    v = axes[idx]
                    if v < -dz and km.get("neg"): should.add(km["neg"])
                    elif v > dz and km.get("pos"): should.add(km["pos"])
                for k in self._pressed - should:
                    try: self._kb.release(k)
                    except: pass
                for k in should - self._pressed:
                    try: self._kb.press(k)
                    except: pass
                self._pressed = should
            except Exception as e:
                logger.error(f"Joystick: {e}")
                time.sleep(1)
            time.sleep(interval)
        self._release_all()

if __name__ == "__main__":
    print("Joystick test — push stick to see values")
    for _ in range(200):
        s = read_joystick()
        if s:
            a = s["axes"]
            print(f"  X:{a[0]:+.2f} Y:{a[1]:+.2f} Z:{a[2]:+.2f} btn:{s['buttons']:04x}")
        else:
            print("  No joystick")
        time.sleep(0.1)
