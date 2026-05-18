import os

# 1. Konten recorded_touches.json (Sudah diset 720x1600)
json_content = """{
  "play_solo": {"x": 360, "y": 1210},
  "continue": {"x": 360, "y": 1350},
  "close": {"x": 650, "y": 100},
  "yes": {"x": 360, "y": 810}
}"""

# 2. Konten auto_cropper.py
cropper_content = """import cv2
import subprocess
import os

SCALE_PERCENT = 40 

def adb(cmd):
    return subprocess.run(f"adb {cmd}", shell=True, capture_output=True, text=True).stdout.strip()

def capture_screen(filename="temp_crop_screen.png"):
    print("\\n[*] Mengambil screenshot dari layar HP...")
    adb(f"shell screencap -p /sdcard/{filename}")
    adb(f"pull /sdcard/{filename} {filename}")
    return filename

def crop_interactive(image_path, button_name, output_filename):
    img = cv2.imread(image_path)
    if img is None:
        print(f"[!] Error: Gambar {image_path} tidak ditemukan.")
        return

    width = int(img.shape[1] * SCALE_PERCENT / 100)
    height = int(img.shape[0] * SCALE_PERCENT / 100)
    resized_img = cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)

    print(f"\\n=========================================")
    print(f"[*] SILAKAN SELEKSI TOMBOL: {button_name}")
    print(f"=========================================")
    print("1. Tahan klik kiri mouse dan tarik kotak pas di area tombol.")
    print("2. Tekan tombol SPASI atau ENTER di keyboard untuk menyimpan.")
    
    window_name = f"Potong Tombol {button_name} (Tekan Spasi/Enter jika sudah pas)"
    roi = cv2.selectROI(window_name, resized_img, showCrosshair=True, fromCenter=False)
    cv2.destroyAllWindows()

    if roi == (0, 0, 0, 0):
        return

    x = int(roi[0] / (SCALE_PERCENT / 100))
    y = int(roi[1] / (SCALE_PERCENT / 100))
    w = int(roi[2] / (SCALE_PERCENT / 100))
    h = int(roi[3] / (SCALE_PERCENT / 100))

    cropped_img = img[y:y+h, x:x+w]
    cv2.imwrite(output_filename, cropped_img)
    print(f"[+] BERHASIL DISIMPAN: {output_filename}")

def main():
    print("=== TOOL AUTO-CROP TOMBOL UI ===")
    input("\\n[TUGAS 1] Buka halaman LOBBY di HP (Ada tombol PLAY SOLO dan X). Tekan ENTER...")
    screen_lobby = capture_screen()
    crop_interactive(screen_lobby, "PLAY SOLO", "tpl_play_solo.png")
    crop_interactive(screen_lobby, "CLOSE (X)", "tpl_close.png")
    
    input("\\n[TUGAS 2] Klik X di HP supaya muncul popup 'YES'. Tekan ENTER...")
    screen_yes = capture_screen()
    crop_interactive(screen_yes, "YES CONFIRM", "tpl_yes.png")

    input("\\n[TUGAS 3] Masuk ke game, lewati Level 1 sampai muncul tombol CONTINUE. Tekan ENTER...")
    screen_continue = capture_screen()
    crop_interactive(screen_continue, "CONTINUE", "tpl_continue.png")

    if os.path.exists("temp_crop_screen.png"):
        os.remove("temp_crop_screen.png")
    print("\\n[+] Selesai! Lanjut ke auto_master_billiard.py")

if __name__ == "__main__":
    main()"""

# 3. Konten auto_master_billiard.py (Sudah diset 720x1600)
bot_content = """import os
import time
import json
import subprocess
import datetime
import google.generativeai as genai
from PIL import Image, ImageDraw
import cv2
import numpy as np

# ==========================================
# 1. KONFIGURASI UTAMA
# ==========================================
GOOGLE_API_KEY = "MASUKKAN_API_KEY_KAMU_DISINI" # <--- GANTI INI!
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})

TOTAL_LEVELS = 18
DEVICE_RES = (720, 1600) # SUDAH DIUPDATE KE 720x1600
TOUCH_FILE = "recorded_touches.json"
FAILED_LOG_FILE = "failed_attempts_log.json"
SCREENSHOT_PATH = "current_screen.png"
GRID_SCREENSHOT_PATH = "grid_screen.png"

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

def wait_for_ui(label, timeout=12, do_tap=True):
    print(f"[*] Menunggu UI: {label}...")
    start = time.time()
    while time.time() - start < timeout:
        if check_ui_exists(label): return True
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

def get_shot_from_ai(level, strategy, failed_attempts):
    img_file = genai.upload_file(path=GRID_SCREENSHOT_PATH)
    failed_context = ""
    if failed_attempts:
        failed_context = "JANGAN GUNAKAN target ini (sudah gagal):\\n" + "\\n".join([f"- X:{f['end_x']}, Y:{f['end_y']}" for f in failed_attempts])
    
    prompt = f\"\"\"
    Screenshot game biliar 720x1600 bergaris grid 100px.
    LEVEL {level} STRATEGI: {strategy}
    {failed_context}
    Output HANYA JSON: {{"start_x":int, "start_y":int, "end_x":int, "end_y":int, "duration_ms":int, "reverse":bool}}
    \"\"\"
    try:
        response = model.generate_content([img_file, prompt])
        return json.loads(response.text)
    except:
        return None
    finally:
        genai.delete_file(img_file.name)

def execute_shot(shot_data):
    sx, sy, ex, ey, dur = shot_data['start_x'], shot_data['start_y'], shot_data['end_x'], shot_data['end_y'], shot_data['duration_ms']
    adb_ex, adb_ey = (sx + (sx - ex), sy + (sy - ey)) if shot_data.get('reverse', False) else (ex, ey)
    adb(f"shell input swipe {sx} {sy} {adb_ex} {adb_ey} {dur}")
    return {"start_x": sx, "start_y": sy, "end_x": adb_ex, "end_y": adb_ey, "duration_ms": dur, "reverse": shot_data.get('reverse', False)}

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
    wait_for_ui("close", 5); wait_for_ui("yes", 5); time.sleep(3)

def replay_to_level(target_level):
    wait_for_ui("play_solo", 10); time.sleep(3)
    for lvl in range(1, target_level):
        shot = json.load(open(f"level_{lvl:02d}_best_shot.json", 'r'))["adb_scaled_shot"]
        adb(f"shell input swipe {shot['start_x']} {shot['start_y']} {shot['end_x']} {shot['end_y']} {shot['duration_ms']}")
        wait_for_ui("continue", 15); time.sleep(2)

def export_macrodroid():
    macrodroid_txt = ["- Tap PLAY SOLO\\n- Wait Level 1"]
    for lvl in range(1, TOTAL_LEVELS + 1):
        if not os.path.exists(f"level_{lvl:02d}_best_shot.json"): continue
        shot = json.load(open(f"level_{lvl:02d}_best_shot.json", 'r'))["adb_scaled_shot"]
        macrodroid_txt.append(f"- Swipe Lvl {lvl} (X:{shot['start_x']},Y:{shot['start_y']} -> X:{shot['end_x']},Y:{shot['end_y']})\\n- Wait CONTINUE")
        if lvl < TOTAL_LEVELS: macrodroid_txt.append(f"- Tap CONTINUE\\n- Wait Level {lvl+1}")
    open("macrodroid_route_steps.txt", "w").write("\\n".join(macrodroid_txt))
    print("\\n[+] RUTE EXPORT MACRODROID SELESAI!")

def main():
    current_level = 1
    wait_for_ui("play_solo", 10); time.sleep(3)
    
    while current_level <= TOTAL_LEVELS:
        best_file = f"level_{current_level:02d}_best_shot.json"
        if os.path.exists(best_file):
            shot = json.load(open(best_file, 'r'))["adb_scaled_shot"]
            adb(f"shell input swipe {shot['start_x']} {shot['start_y']} {shot['end_x']} {shot['end_y']} {shot['duration_ms']}")
            wait_for_ui("continue", 15); time.sleep(2)
            current_level += 1
            continue
            
        print(f"\\n=== MENGANALISA LEVEL {current_level} DENGAN AI ===")
        capture_screen(SCREENSHOT_PATH); apply_grid_overlay(SCREENSHOT_PATH, GRID_SCREENSHOT_PATH)
        fails = json.load(open(FAILED_LOG_FILE, 'r')).get(str(current_level), []) if os.path.exists(FAILED_LOG_FILE) else []
        shot_plan = get_shot_from_ai(current_level, LEVEL_STRATEGY.get(current_level, ""), fails)
        
        if not shot_plan: time.sleep(5); continue
        adb_scaled = execute_shot(shot_plan); time.sleep(3)
        
        if wait_for_ui("continue", 12, True):
            save_best(current_level, shot_plan, adb_scaled); time.sleep(2); current_level += 1
        else:
            log_failed(current_level, shot_plan); recover_to_start(); replay_to_level(current_level)
            
    export_macrodroid()

if __name__ == "__main__":
    main()"""

# Eksekusi pembuatan file
with open("recorded_touches.json", "w") as f:
    f.write(json_content)
with open("auto_cropper.py", "w") as f:
    f.write(cropper_content)
with open("auto_master_billiard.py", "w") as f:
    f.write(bot_content)

print("[SUCCESS] 3 File berhasil dibuat di folder ini!")
print("1. recorded_touches.json (Sudah 720x1600)")
print("2. auto_cropper.py")
print("3. auto_master_billiard.py (Sudah 720x1600)")