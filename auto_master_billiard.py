import os
import time
import json
import subprocess
import datetime
import cv2
import numpy as np
from PIL import Image, ImageDraw

# MENGGUNAKAN MODUL LAMA YANG STABIL DI LAPTOPMU
import google.generativeai as genai

# ==========================================
# 1. KONFIGURASI UTAMA & BACA API KEY
# ==========================================
try:
    with open("config.json", "r") as f:
        config_data = json.load(f)
        GOOGLE_API_KEY = config_data.get("API_KEY", "")
except FileNotFoundError:
    print("[!] ERROR: File config.json tidak ditemukan!")
    print("[!] Buat file config.json di folder ini dengan isi: {\"API_KEY\": \"kode_rahasia_kamu\"}")
    exit()

if not GOOGLE_API_KEY or GOOGLE_API_KEY == "MASUKKAN_API_KEY_KAMU_DISINI":
    print("[!] ERROR: API Key di config.json belum diganti dengan yang asli!")
    exit()

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})

TOTAL_LEVELS = 18
DEVICE_RES = (720, 1600)
TOUCH_FILE = "recorded_touches.json"
FAILED_LOG_FILE = "failed_attempts_log.json"
SCREENSHOT_PATH = "current_screen.png"
GRID_SCREENSHOT_PATH = "grid_screen.png"

# ==========================================
# DATA KOORDINAT DROP PAS DI BOLA (HASIL RICEK USER)
# ==========================================
DROP_COORDINATES = {
    1: (371, 1281),
    2: (400, 1288),
    3: (376, 1309),
    4: (380, 1293),
    5: (389, 1283),
    6: (384, 1302),
    7: (401, 1298),
    8: (386, 1257),
    9: (398, 1274),
    10: (378, 1298),
    11: (398, 1305),
    12: (378, 1286),
    13: (393, 1294),
    14: (401, 1309),
    15: (383, 1341),
    16: (388, 1313),
    17: (343, 1075),
    18: (525, 1306)
}

LEVEL_STRATEGY = {
    1: "Pantulan kanan (right wall bank). Jangan tembak lurus.",
    2: "Cari celah pantulan, hindari area tengah.",
    3: "Prioritas lane tengah ikuti up-arrow.",
    4: "Jalur kiri/up-arrow kiri lebih aman.",
    5: "Lewati area center/cyan lane.",
    6: "Akurasi celah tengah lebih penting dari power.",
    7: "Jalur aman lewat sisi kiri/atas ikuti kemiringan.",
    8: "Cari pantulan ke arah kiri target.",
    9: "Gunakan portal HANYA jika mengarah ke target.",
    10: "Rute kiri/kanan, cek up-arrow mana yang aman.",
    11: "Windmill di tengah, cari jalur sisi kiri.",
    12: "Gunakan rute sisi kanan melewati penghalang.",
    13: "Awas hole portal/trap. Arahkan ke flagged hole.",
    14: "Gunakan jalur tengah ikuti arrow.",
    15: "Power cukup besar lurus stabil di jalur vertikal.",
    16: "Cari jalur kiri lewati obstacle vertikal.",
    17: "Gunakan shot pendek/direct, koreksi arah kecil.",
    18: "Bisa pakai bottom bank untuk lewat obstacle."
}

def adb(cmd):
    return subprocess.run(f"adb {cmd}", shell=True, capture_output=True, text=True).stdout.strip()

def capture_screen(filename=SCREENSHOT_PATH):
    adb(f"shell screencap -p /sdcard/{filename}")
    adb(f"pull /sdcard/{filename} {filename}")
    return filename

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
    print(f"[*] Mengecek keberadaan UI: '{label}' ...")
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
                        print(f"[+] UI '{label}' muncul! Layar siap.")
                        return True
        else:
            if check_ui_exists(label): 
                return True
        time.sleep(1)
        
    if do_tap: tap_button(label)
    return False

def apply_grid_overlay(image_path, output_path, step=100):
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    width, height = img.size
    for x in range(0, width, step):
        draw.line([(x, 0), (x, height)], fill=(255, 0, 0, 128), width=2)
        draw.text((x + 2, 10), str(x), fill=(255, 255, 0))
    for y in range(0, height, step):
        draw.line([(0, y), (width, y)], fill=(0, 255, 0, 128), width=2)
        draw.text((10, y + 2), str(y), fill=(255, 255, 0))
    img.save(output_path)
    return output_path

def drop_ball_fixed(level):
    x, y = DROP_COORDINATES.get(level, (360, 1300))
    print(f"[+] FIXED DROP LEVEL {level}: Melakukan TAP pas di koordinat bola (X:{x}, Y:{y})...")
    adb(f"shell input tap {x} {y}")
    time.sleep(2) # Tunggu bola jatuh ke meja dan anteng sempurna
    return x, y

def get_shot_from_ai(level, strategy, failed_attempts):
    img_file = genai.upload_file(path=GRID_SCREENSHOT_PATH)
    failed_context = ""
    if failed_attempts:
        failed_context = "JANGAN GUNAKAN target ini (sudah gagal):\n" + "\n".join([f"- X:{f['end_x']}, Y:{f['end_y']}" for f in failed_attempts])
    
    prompt = f"""
    Screenshot game biliar 720x1600 bergaris grid 100px.
    BOLA SUDAH BERADA DI ATAS MEJA.
    LEVEL {level} STRATEGI: {strategy}
    {failed_context}
    
    TUGAS:
    1. Cari titik tengah bola asli di atas meja (start_x, start_y).
    2. Tentukan target sasaran pantulan/lubang (end_x, end_y).
    Output HANYA JSON: {{"start_x":int, "start_y":int, "end_x":int, "end_y":int, "duration_ms":int, "reverse":bool}}
    """
    try:
        response = model.generate_content([img_file, prompt])
        return json.loads(response.text)
    except Exception as e:
        print(f"[-] Error AI Shot: {e}")
        return None
    finally:
        genai.delete_file(img_file.name)

def execute_shot(shot_data):
    sx, sy, ex, ey, dur = shot_data['start_x'], shot_data['start_y'], shot_data['end_x'], shot_data['end_y'], shot_data['duration_ms']
    adb_ex, adb_ey = (sx + (sx - ex), sy + (sy - ex)) if shot_data.get('reverse', False) else (ex, ey)
    
    print(f"[*] AI MENGIRIM TEMBAKAN: Dari ({sx}, {sy}) ke arah ({adb_ex}, {adb_ey}) dengan power {dur}ms")
    adb(f"shell input swipe {sx} {sy} {adb_ex} {adb_ey} {dur}")
    time.sleep(1) # JEDA SETELAH SWIPE TEMBAKAN
    
    return {"drop_x": shot_data.get('drop_x', sx), "drop_y": shot_data.get('drop_y', sy), 
            "start_x": sx, "start_y": sy, "end_x": adb_ex, "end_y": adb_ey, 
            "duration_ms": dur, "reverse": shot_data.get('reverse', False)}

def log_failed(level, shot_data):
    fails = json.load(open(FAILED_LOG_FILE, 'r')) if os.path.exists(FAILED_LOG_FILE) else {}
    fails.setdefault(str(level), []).append(shot_data)
    json.dump(fails, open(FAILED_LOG_FILE, 'w'), indent=2)

def save_best(level, ai_raw, adb_scaled):
    file_name = f"level_{level:02d}_best_shot.json"
    data = {"level": level, "adb_scaled_shot": adb_scaled, "saved_at": datetime.datetime.now().isoformat()}
    json.dump(data, open(file_name, 'w'), indent=2)
    print(f"[+] BEST SHOT Level {level} TERSIMPAN!")

def recover_to_start():
    wait_for_ui("close", 5, do_tap=True)
    wait_for_ui("yes", 5, do_tap=True) 
    time.sleep(4)

def replay_to_level(target_level):
    wait_for_ui("play_solo", 10, do_tap=True)
    
    print("[*] CEK & RICEK: Menunggu game loading masuk ke level 1...")
    wait_for_ui("close", timeout=20, do_tap=False)
    time.sleep(1)
    
    for lvl in range(1, target_level):
        dx, dy = drop_ball_fixed(lvl)
        shot = json.load(open(f"level_{lvl:02d}_best_shot.json", 'r'))["adb_scaled_shot"]
        
        print(f"[*] Replay otomatis Level {lvl} - Menembak...")
        adb(f"shell input swipe {shot['start_x']} {shot['start_y']} {shot['end_x']} {shot['end_y']} {shot['duration_ms']}")
        time.sleep(1)
        
        wait_for_ui("continue", 15, do_tap=True)
        print(f"[*] CEK & RICEK: Menunggu Level {lvl+1} selesai loading...")
        wait_for_ui("close", timeout=20, do_tap=False)
        time.sleep(1)

def export_macrodroid():
    macrodroid_txt = ["- Tap PLAY SOLO\n- Wait Level 1"]
    for lvl in range(1, TOTAL_LEVELS + 1):
        if not os.path.exists(f"level_{lvl:02d}_best_shot.json"): continue
        shot = json.load(open(f"level_{lvl:02d}_best_shot.json", 'r'))["adb_scaled_shot"]
        dx, dy = DROP_COORDINATES.get(lvl, (360, 1300))
        
        macrodroid_txt.append(f"- Tap DROP BOLA FIXED (X:{dx}, Y:{dy})\n- Wait 2s")
        macrodroid_txt.append(f"- Swipe Lvl {lvl} (X:{shot['start_x']},Y:{shot['start_y']} -> X:{shot['end_x']},Y:{shot['end_y']})\n- Wait 1s\n- Wait CONTINUE")
        if lvl < TOTAL_LEVELS: macrodroid_txt.append(f"- Tap CONTINUE\n- Wait Next Level Ready")
    open("macrodroid_route_steps.txt", "w").write("\n".join(macrodroid_txt))
    print("\n[+] RUTE EXPORT MACRODROID SELESAI!")

def main():
    current_level = 1
    wait_for_ui("play_solo", 10, do_tap=True)
    
    print("[*] CEK & RICEK: Menunggu loading masuk ke level 1...")
    wait_for_ui("close", timeout=20, do_tap=False)
    time.sleep(1)
    
    while current_level <= TOTAL_LEVELS:
        # DROP BOLA DI AWAL LOOP LEVEL MENGGUNAKAN KOORDINAT ASLI DARI KAMU
        drop_x, drop_y = drop_ball_fixed(current_level)
        
        best_file = f"level_{current_level:02d}_best_shot.json"
        if os.path.exists(best_file):
            shot = json.load(open(best_file, 'r'))["adb_scaled_shot"]
            
            print(f"[*] Eksekusi Best Shot Jalan Tol Level {current_level}...")
            adb(f"shell input swipe {shot['start_x']} {shot['start_y']} {shot['end_x']} {shot['end_y']} {shot['duration_ms']}")
            time.sleep(1)
            
            wait_for_ui("continue", 15, do_tap=True)
            print("[*] CEK & RICEK: Menunggu Level Berikutnya selesai loading...")
            wait_for_ui("close", timeout=20, do_tap=False)
            time.sleep(1)
            current_level += 1
            continue
            
        print(f"\n=== MENGANALISA TEMBAKAN LEVEL {current_level} DENGAN AI ===")
        print("[*] MENGAMBIL SCREENSHOT MEJA: Kondisi bola sudah mendarat anteng...")
        capture_screen(SCREENSHOT_PATH); apply_grid_overlay(SCREENSHOT_PATH, GRID_SCREENSHOT_PATH)
        fails = json.load(open(FAILED_LOG_FILE, 'r')).get(str(current_level), []) if os.path.exists(FAILED_LOG_FILE) else []
        
        shot_plan = get_shot_from_ai(current_level, LEVEL_STRATEGY.get(current_level, ""), fails)
        if not shot_plan: time.sleep(5); continue
        
        shot_plan['drop_x'] = drop_x
        shot_plan['drop_y'] = drop_y
        
        adb_scaled = execute_shot(shot_plan)
        time.sleep(3)
        
        if wait_for_ui("continue", 12, do_tap=True):
            save_best(current_level, shot_plan, adb_scaled)
            print("[*] CEK & RICEK: Menunggu Level Berikutnya selesai loading...")
            wait_for_ui("close", timeout=20, do_tap=False)
            time.sleep(1)
            current_level += 1
        else:
            log_failed(current_level, shot_plan); recover_to_start(); replay_to_level(current_level)
            
    export_macrodroid()

if __name__ == "__main__":
    main()