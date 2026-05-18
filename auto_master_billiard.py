import os
import time
import json
import subprocess
import datetime

# ==========================================
# 1. KONFIGURASI UTAMA
# ==========================================
TOTAL_LEVELS = 18
TOUCH_FILE = "recorded_touches.json"
SCREENSHOT_PATH = "current_screen.png"

# ==========================================
# HARDCODED ACTIONS PER LEVEL (SUDAH TERBUKTI BERHASIL)
# Level 1 tetap pakai best_shot file (jalan tol lama)
# Level 2-18 pakai actions dari data rekaman
# ==========================================
LEVEL_ACTIONS = {
    2: [
        {"type": "swipe", "x1": 408, "y1": 1273, "x2": 375, "y2": 1246, "duration": 150, "delay_before": 0.0},
        {"type": "swipe", "x1": 210, "y1": 789,  "x2": 622, "y2": 1012, "duration": 1000, "delay_before": 0.5},
        {"type": "swipe", "x1": 530, "y1": 759,  "x2": 149, "y2": 874,  "duration": 1977, "delay_before": 5.0},
        {"type": "tap",   "x":  401, "y":  1068,                          "delay_before": 2.0},
    ],
    3: [
        {"type": "swipe", "x1": 407, "y1": 1307, "x2": 425, "y2": 1281, "duration": 150,  "delay_before": 0.0},
        {"type": "swipe", "x1": 441, "y1": 1041, "x2": 504, "y2": 1253, "duration": 1000, "delay_before": 0.5},
        {"type": "swipe", "x1": 432, "y1": 890,  "x2": 480, "y2": 1018, "duration": 1038, "delay_before": 5.8},
        {"type": "swipe", "x1": 558, "y1": 794,  "x2": 174, "y2": 817,  "duration": 2686, "delay_before": 3.7},
        {"type": "tap",   "x":  438, "y":  1070,                          "delay_before": 2.0},
    ],
    4: [
        {"type": "swipe", "x1": 401, "y1": 1292, "x2": 433, "y2": 1254, "duration": 150,  "delay_before": 0.0},
        {"type": "swipe", "x1": 375, "y1": 1333, "x2": 280, "y2": 1432, "duration": 1000, "delay_before": 0.5},
        {"type": "swipe", "x1": 162, "y1": 809,  "x2": 583, "y2": 779,  "duration": 2702, "delay_before": 5.0},
        {"type": "tap",   "x":  311, "y":  1066,                          "delay_before": 2.0},
    ],
    5: [
        {"type": "swipe", "x1": 391, "y1": 1267, "x2": 326, "y2": 1219, "duration": 150,  "delay_before": 0.0},
        {"type": "swipe", "x1": 549, "y1": 468,  "x2": 467, "y2": 1226, "duration": 1000, "delay_before": 0.5},
        {"type": "tap",   "x":  399, "y":  1067,                          "delay_before": 2.0},
    ],
    6: [
        {"type": "swipe", "x1": 405, "y1": 1312, "x2": 306, "y2": 1246, "duration": 150,  "delay_before": 0.0},
        {"type": "swipe", "x1": 604, "y1": 521,  "x2": 478, "y2": 1308, "duration": 1000, "delay_before": 1.5},
        {"type": "tap",   "x":  394, "y":  1072,                          "delay_before": 2.0},
    ],
    7: [
        {"type": "swipe", "x1": 403, "y1": 1308, "x2": 570, "y2": 1233, "duration": 150,  "delay_before": 0.0},
        {"type": "swipe", "x1": 363, "y1": 492,  "x2": 555, "y2": 1184, "duration": 1000, "delay_before": 0.5},
        {"type": "tap",   "x":  376, "y":  1068,                          "delay_before": 2.0},
    ],
    8: [
        {"type": "swipe", "x1": 391, "y1": 1251, "x2": 358, "y2": 1232, "duration": 150,  "delay_before": 0.0},
        {"type": "swipe", "x1": 553, "y1": 856,  "x2": 275, "y2": 1317, "duration": 1000, "delay_before": 0.5},
        {"type": "swipe", "x1": 384, "y1": 1094, "x2": 636, "y2": 927,  "duration": 1565, "delay_before": 5.7},
        {"type": "tap",   "x":  401, "y":  1072,                          "delay_before": 2.0},
    ],
    9: [
        {"type": "tap",   "x":  388, "y":  1274,                          "delay_before": 0.0},
        {"type": "swipe", "x1": 457, "y1": 1185, "x2": 471, "y2": 1330, "duration": 1000, "delay_before": 0.5},
        {"type": "swipe", "x1": 450, "y1": 1091, "x2": 172, "y2": 1068, "duration": 955,  "delay_before": 6.1},
        {"type": "tap",   "x":  400, "y":  1042,                          "delay_before": 2.0},
    ],
    10: [
        {"type": "swipe", "x1": 381, "y1": 1290, "x2": 318, "y2": 1273, "duration": 150,  "delay_before": 0.0},
        {"type": "swipe", "x1": 479, "y1": 406,  "x2": 463, "y2": 1189, "duration": 1000, "delay_before": 0.5},
        {"type": "tap",   "x":  401, "y":  1090,                          "delay_before": 2.0},
    ],
    11: [
        {"type": "tap",   "x":  400, "y":  1308,                          "delay_before": 0.0},
        {"type": "swipe", "x1": 413, "y1": 800,  "x2": 567, "y2": 1227, "duration": 1000, "delay_before": 0.5},
        {"type": "swipe", "x1": 408, "y1": 900,  "x2": 617, "y2": 480,  "duration": 2043, "delay_before": 3.3},
        {"type": "tap",   "x":  388, "y":  1049,                          "delay_before": 2.0},
    ],
    12: [
        {"type": "swipe", "x1": 372, "y1": 1288, "x2": 355, "y2": 1220, "duration": 150,  "delay_before": 0.0},
        {"type": "swipe", "x1": 536, "y1": 906,  "x2": 530, "y2": 1113, "duration": 1000, "delay_before": 0.5},
        {"type": "swipe", "x1": 540, "y1": 987,  "x2": 457, "y2": 984,  "duration": 2011, "delay_before": 4.7},
        {"type": "swipe", "x1": 519, "y1": 1096, "x2": 527, "y2": 645,  "duration": 1516, "delay_before": 4.7},
        {"type": "tap",   "x":  407, "y":  1053,                          "delay_before": 2.0},
    ],
    13: [
        {"type": "swipe", "x1": 405, "y1": 1292, "x2": 320, "y2": 1245, "duration": 150,  "delay_before": 0.0},
        {"type": "swipe", "x1": 203, "y1": 1041, "x2": 615, "y2": 1292, "duration": 1000, "delay_before": 0.5},
        {"type": "tap",   "x":  446, "y":  1081,                          "delay_before": 2.0},
    ],
    14: [
        {"type": "swipe", "x1": 403, "y1": 1310, "x2": 347, "y2": 1288, "duration": 150,  "delay_before": 0.0},
        {"type": "swipe", "x1": 520, "y1": 400,  "x2": 488, "y2": 1306, "duration": 1000, "delay_before": 0.5},
        {"type": "tap",   "x":  373, "y":  1075,                          "delay_before": 2.0},
    ],
    15: [
        {"type": "swipe", "x1": 373, "y1": 1337, "x2": 530, "y2": 1313, "duration": 150,  "delay_before": 0.0},
        {"type": "swipe", "x1": 397, "y1": 421,  "x2": 549, "y2": 1356, "duration": 1000, "delay_before": 0.5},
        {"type": "tap",   "x":  413, "y":  1077,                          "delay_before": 2.0},
    ],
    16: [
        {"type": "swipe", "x1": 396, "y1": 1311, "x2": 437, "y2": 1274, "duration": 150,  "delay_before": 0.0},
        {"type": "swipe", "x1": 578, "y1": 858,  "x2": 300, "y2": 1438, "duration": 1000, "delay_before": 0.5},
        {"type": "tap",   "x":  443, "y":  1073,                          "delay_before": 2.0},
    ],
    17: [
        {"type": "swipe", "x1": 359, "y1": 1062, "x2": 381, "y2": 1032, "duration": 394,  "delay_before": 0.0},
        {"type": "swipe", "x1": 363, "y1": 817,  "x2": 433, "y2": 1263, "duration": 1631, "delay_before": 0.9},
        {"type": "swipe", "x1": 340, "y1": 1307, "x2": 225, "y2": 1311, "duration": 3709, "delay_before": 4.0},
        {"type": "swipe", "x1": 429, "y1": 1253, "x2": 468, "y2": 1338, "duration": 741,  "delay_before": 4.1},
        {"type": "tap",   "x":  443, "y":  1073,                          "delay_before": 2.0},
    ],
    18: [
        {"type": "swipe", "x1": 530, "y1": 1299, "x2": 520, "y2": 1258, "duration": 150,  "delay_before": 0.0},
        {"type": "swipe", "x1": 554, "y1": 1254, "x2": 534, "y2": 1374, "duration": 1000, "delay_before": 0.5},
        {"type": "swipe", "x1": 434, "y1": 511,  "x2": 337, "y2": 409,  "duration": 2324, "delay_before": 5.0},
        {"type": "swipe", "x1": 313, "y1": 1221, "x2": 242, "y2": 1230, "duration": 658,  "delay_before": 6.7},
    ],
}

# Level 1 tetap pakai best_shot file
LEVEL_1_SHOT_FILE = "level_01_best_shot.json"

def adb(cmd):
    return subprocess.run(f"adb {cmd}", shell=True, capture_output=True, text=True).stdout.strip()

def capture_screen(filename=SCREENSHOT_PATH):
    adb(f"shell screencap -p /sdcard/{filename}")
    adb(f"pull /sdcard/{filename} {filename}")

def load_touches():
    if os.path.exists(TOUCH_FILE):
        with open(TOUCH_FILE, 'r') as f:
            return json.load(f)
    return {}
TOUCHES = load_touches()

def tap_button(label):
    if label in TOUCHES:
        x, y = TOUCHES[label]["x"], TOUCHES[label]["y"]
        adb(f"shell input tap {x} {y}")

def check_ui_exists(template_name, threshold=0.8):
    import cv2, numpy as np
    template_path = f"tpl_{template_name}.png"
    if not os.path.exists(template_path): return False
    capture_screen("temp_vision.png")
    img = cv2.imread("temp_vision.png", 0)
    template = cv2.imread(template_path, 0)
    if img is None or template is None: return False
    res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
    loc = np.where(res >= threshold)
    if len(loc[0]) > 0:
        y, x = loc[0][0], loc[1][0]
        h, w = template.shape
        adb(f"shell input tap {x + w//2} {y + h//2}")
        return True
    return False

def wait_for_ui(label, timeout=15, do_tap=True):
    print(f"[*] Menunggu UI: '{label}' ...")
    import cv2, numpy as np
    start = time.time()
    while time.time() - start < timeout:
        if not do_tap:
            template_path = f"tpl_{label}.png"
            if os.path.exists(template_path):
                capture_screen("temp_vision.png")
                img = cv2.imread("temp_vision.png", 0)
                template = cv2.imread(template_path, 0)
                if img is not None and template is not None:
                    res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
                    loc = np.where(res >= 0.8)
                    if len(loc[0]) > 0:
                        print(f"[+] UI '{label}' muncul!")
                        return True
        else:
            if check_ui_exists(label):
                return True
        time.sleep(1)
    if do_tap: tap_button(label)
    return False

def execute_actions(level):
    """Eksekusi semua actions untuk level tertentu."""
    actions = LEVEL_ACTIONS.get(level, [])
    print(f"[*] Eksekusi {len(actions)} actions untuk Level {level}...")
    for i, action in enumerate(actions):
        delay = action.get("delay_before", 0)
        if delay > 0:
            print(f"    [~] Delay {delay:.1f}s sebelum action {i+1}...")
            time.sleep(delay)
        if action["type"] == "swipe":
            x1, y1, x2, y2, dur = action["x1"], action["y1"], action["x2"], action["y2"], action["duration"]
            print(f"    [>] Swipe ({x1},{y1}) -> ({x2},{y2}) dur:{dur}ms")
            adb(f"shell input swipe {x1} {y1} {x2} {y2} {dur}")
        elif action["type"] == "tap":
            x, y = action["x"], action["y"]
            print(f"    [>] Tap ({x},{y})")
            adb(f"shell input tap {x} {y}")

def execute_level1():
    """Level 1 pakai best_shot file yang sudah terbukti berhasil."""
    if not os.path.exists(LEVEL_1_SHOT_FILE):
        print(f"[!] File {LEVEL_1_SHOT_FILE} tidak ditemukan!")
        return False
    shot = json.load(open(LEVEL_1_SHOT_FILE, 'r'))["adb_scaled_shot"]
    print(f"[*] Eksekusi Level 1 (best_shot): ({shot['start_x']},{shot['start_y']}) -> ({shot['end_x']},{shot['end_y']}) {shot['duration_ms']}ms")
    adb(f"shell input swipe {shot['start_x']} {shot['start_y']} {shot['end_x']} {shot['end_y']} {shot['duration_ms']}")
    return True

def export_macrodroid():
    lines = ["=== MACRODROID ROUTE ===", "- Tap PLAY SOLO", "- Wait Level 1 ready", ""]
    # Level 1
    if os.path.exists(LEVEL_1_SHOT_FILE):
        shot = json.load(open(LEVEL_1_SHOT_FILE, 'r'))["adb_scaled_shot"]
        lines.append(f"Level 1:")
        lines.append(f"  Swipe ({shot['start_x']},{shot['start_y']}) -> ({shot['end_x']},{shot['end_y']}) {shot['duration_ms']}ms")
        lines.append(f"  Tap CONTINUE")
        lines.append("")
    # Level 2-18
    for lvl in range(2, TOTAL_LEVELS + 1):
        actions = LEVEL_ACTIONS.get(lvl, [])
        if not actions: continue
        lines.append(f"Level {lvl}:")
        for a in actions:
            if a["type"] == "swipe":
                lines.append(f"  delay {a['delay_before']}s -> Swipe ({a['x1']},{a['y1']}) -> ({a['x2']},{a['y2']}) {a['duration']}ms")
            elif a["type"] == "tap":
                lines.append(f"  delay {a['delay_before']}s -> Tap ({a['x']},{a['y']})")
        lines.append(f"  Tap CONTINUE")
        lines.append("")
    open("macrodroid_route_steps.txt", "w").write("\n".join(lines))
    print("[+] MACRODROID EXPORT SELESAI!")

def main():
    wait_for_ui("play_solo", 10, do_tap=True)
    print("[*] Menunggu loading masuk ke level 1...")
    wait_for_ui("close", timeout=20, do_tap=False)
    time.sleep(1)

    for current_level in range(1, TOTAL_LEVELS + 1):
        print(f"\n{'='*40}")
        print(f"[*] LEVEL {current_level}")
        print(f"{'='*40}")

        if current_level == 1:
            execute_level1()
        else:
            execute_actions(current_level)

        # Tunggu continue / next level
        print(f"[*] Menunggu CONTINUE / next level...")
        if current_level < TOTAL_LEVELS:
            wait_for_ui("continue", 20, do_tap=True)
            print(f"[*] Menunggu level {current_level + 1} loading...")
            wait_for_ui("close", timeout=20, do_tap=False)
            time.sleep(1)
        else:
            print("[+] SEMUA LEVEL SELESAI!")

    export_macrodroid()

if __name__ == "__main__":
    main()
