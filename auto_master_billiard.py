import os
import time
import json
import subprocess
import datetime
import base64
import cv2
import numpy as np
from PIL import Image, ImageDraw
from groq import Groq

# ==========================================
# 1. KONFIGURASI UTAMA & BACA API KEY
# ==========================================
try:
    with open("config.json", "r") as f:
        config_data = json.load(f)
        GROQ_API_KEY = config_data.get("GROQ_API_KEY", "")
except FileNotFoundError:
    print("[!] ERROR: File config.json tidak ditemukan!")
    print('[!] Buat file config.json dengan isi: {"GROQ_API_KEY": "gsk_xxxx"}')
    exit()

if not GROQ_API_KEY or GROQ_API_KEY == "MASUKKAN_GROQ_API_KEY_DISINI":
    print("[!] ERROR: GROQ_API_KEY di config.json belum diisi!")
    exit()

client = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

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
    1: (
        "Ada obstacle di tengah/jalur langsung. "
        "Shot yang terbukti: pantulan kanan (right wall bank). "
        "JANGAN tembak lurus ke obstacle. "
        "Level 1 dipakai sebagai replay jalan tol, jangan ubah kalau best_shot sudah ada."
    ),
    2: (
        "Ada beberapa obstacle/bar yang menghalangi jalur langsung. "
        "JANGAN tembak lurus menabrak bar. "
        "Cari jalur bank/pantulan yang melewati CELAH di antara bar. "
        "Identifikasi ruang kosong di antara obstacle lalu arahkan bola lewat celah tersebut."
    ),
    3: (
        "Jalur utama lewat area TENGAH. "
        "Ada up-arrow/guide di tengah sebagai petunjuk arah. "
        "Prioritas lintasan masuk melalui lane tengah, bukan menabrak sisi obstacle. "
        "Kalau swipe normal kebalik hasilnya, gunakan reverse=true."
    ),
    4: (
        "Ada jalur kiri / area up-arrow kiri yang lebih aman. "
        "Hindari hole/trap bawah kanan kecuali itu portal yang menuju target. "
        "Utamakan jalur yang memanfaatkan sisi kiri untuk menuju target."
    ),
    5: (
        "Jalur relatif melalui lane tengah / cyan lane. "
        "Cari shot yang melewati area center. "
        "JANGAN terlalu melebar ke obstacle samping."
    ),
    6: (
        "Layout seperti hourglass/gate sempit. "
        "Shot HARUS melewati celah tengah yang sempit. "
        "Akurasi arah lebih penting dari power. "
        "Power boleh besar selama bola melewati hole/target tanpa menabrak tepi gate."
    ),
    7: (
        "Ada koridor miring/slanted corridor. "
        "Jalur aman lewat sisi kiri/atas atau mengikuti kemiringan obstacle. "
        "JANGAN tembak lurus kalau jalurnya menabrak obstacle miring."
    ),
    8: (
        "Target/jalur cenderung ke sisi KIRI. "
        "Cari pantulan atau route yang mengarah ke kiri target. "
        "Hindari terlalu kanan jika ada obstacle menghalangi."
    ),
    9: (
        "Ada kemungkinan hole trap/portal. "
        "JANGAN langsung anggap semua hole sebagai target. "
        "Gunakan portal HANYA kalau keluarnya mengarah ke target asli. "
        "Kalau portal tidak terbukti membantu, gunakan safe bridge/lane."
    ),
    10: (
        "Ada dua kemungkinan rute: kiri dan kanan. "
        "Cek up-arrow kiri atau kanan yang lebih aman. "
        "Hindari jalur tengah kalau tertutup obstacle. "
        "Boleh coba left route atau right route."
    ),
    11: (
        "Ada obstacle bergerak/windmill di area tengah. HINDARI pusat obstacle. "
        "Timing bisa berpengaruh jika obstacle bergerak. "
        "Cari jalur sisi kiri/aman yang tidak menabrak bagian tengah windmill."
    ),
    12: (
        "Ada obstacle/tembok tengah. "
        "Jalur cenderung dari sisi KANAN. "
        "Gunakan route kanan untuk melewati penghalang tengah lalu menuju target."
    ),
    13: (
        "Target asli adalah hole yang berflag/tujuan akhir, bukan semua lubang. "
        "Ada kemungkinan hole portal/trap. "
        "Jika memakai portal simpan uses_portal=true. "
        "Kalau tidak memakai portal, hindari hole trap dan arahkan ke flagged target."
    ),
    14: (
        "Layout seperti funnel/center route. "
        "Gunakan jalur TENGAH mengikuti arrow/funnel. "
        "JANGAN terlalu menyamping karena bisa mentok obstacle."
    ),
    15: (
        "Ada jalur vertikal/center shaft. "
        "Shot perlu power CUKUP BESAR melalui jalur tengah. "
        "Arah harus lurus/stabil agar tidak menyentuh dinding shaft."
    ),
    16: (
        "Jalur target cenderung sisi KIRI. "
        "Ada stack/obstacle vertikal yang harus dihindari. "
        "Cari jalur kiri yang melewati obstacle, bukan tembak langsung ke stack."
    ),
    17: (
        "Target relatif dekat / short route. "
        "JANGAN overcomplicate. "
        "Gunakan shot pendek/direct jika memungkinkan. "
        "Kalau ada obstacle kecil, koreksi arah sedikit saja."
    ),
    18: (
        "Target akhir cenderung bawah/kiri atau perlu route bawah. "
        "Ada kemungkinan portal/trap sisi kanan. "
        "JANGAN langsung masuk portal kecuali jelas membantu menuju target. "
        "Bisa pakai bottom bank/pantulan bawah untuk melewati obstacle. "
        "Setelah Level 18 cukup simpan best_shot saja."
    ),
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
    time.sleep(2)
    return x, y

def encode_image_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def get_shot_from_ai(level, strategy, failed_attempts):
    failed_context = ""
    if failed_attempts:
        failed_context = (
            "PERCOBAAN GAGAL SEBELUMNYA - JANGAN gunakan koordinat end ini lagi:\n"
            + "\n".join([f"  - end_x:{f['end_x']}, end_y:{f['end_y']}" for f in failed_attempts])
            + "\nPilih arah yang BERBEDA dari daftar di atas.\n"
        )

    system_prompt = (
        "Kamu adalah AI analis game biliar. "
        "Tugasmu HANYA menganalisis screenshot dan memberikan koordinat tembakan yang TIDAK menabrak obstacle. "
        "ATURAN WAJIB:\n"
        "1. IDENTIFIKASI semua obstacle/bar/penghalang di layar terlebih dahulu.\n"
        "2. PASTIKAN lintasan dari start ke end TIDAK melewati obstacle apapun.\n"
        "3. Cari CELAH atau jalur kosong yang bisa dilalui bola.\n"
        "4. end_x/end_y adalah titik TUJUAN/TARGET/LUBANG, bukan obstacle.\n"
        "5. Jika jalur lurus terblokir, gunakan pantulan dinding (bank shot).\n"
        "6. Output HANYA JSON murni, tanpa teks, komentar, atau markdown apapun."
    )

    user_prompt = (
        f"Ini screenshot game biliar 720x1600 dengan overlay grid 100px.\n"
        f"Bola sudah ada di atas meja (jangan drop lagi).\n\n"
        f"=== LEVEL {level} ===\n"
        f"PANDUAN STRATEGI: {strategy}\n\n"
        f"{failed_context}"
        f"LANGKAH ANALISIS:\n"
        f"1. Temukan posisi tengah BOLA di meja -> (start_x, start_y)\n"
        f"2. Identifikasi semua OBSTACLE (bar/dinding/penghalang) - JANGAN jadikan ini target\n"
        f"3. Temukan LUBANG/HOLE TARGET atau CELAH yang kosong -> (end_x, end_y)\n"
        f"4. Pastikan garis dari start ke end TIDAK melewati obstacle\n"
        f"5. POWER otomatis maksimal, jangan khawatir soal kecepatan.\n"
        f"   Kamu cukup tentukan ARAH yang tepat saja.\n\n"
        f"Output HANYA JSON ini (tanpa duration_ms):\n"
        f'{{ "start_x": int, "start_y": int, "end_x": int, "end_y": int }}'
    )

    try:
        img_b64 = encode_image_base64(GRID_SCREENSHOT_PATH)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_b64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": user_prompt
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_tokens=300,
        )
        raw = response.choices[0].message.content.strip()
        print(f"[AI RAW RESPONSE] {raw}")
        # Bersihkan jika ada markdown code block
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        # Ambil hanya bagian JSON { ... }
        start_idx = raw.find("{")
        end_idx = raw.rfind("}") + 1
        if start_idx != -1 and end_idx > start_idx:
            raw = raw[start_idx:end_idx]
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        # Fallback: paksa default duration kalau key hilang
        try:
            parsed = json.loads(raw.strip())
            parsed.setdefault("duration_ms", 500)
            parsed.setdefault("reverse", False)
            return parsed
        except Exception as e2:
            print(f"[-] Error parse JSON: {e2}")
            return None
    except Exception as e:
        print(f"[-] Error AI Shot: {e}")
        return None

def execute_shot(shot_data):
    sx, sy, ex, ey = shot_data['start_x'], shot_data['start_y'], shot_data['end_x'], shot_data['end_y']

    # Hitung vektor arah dari bola ke target (target = arah tujuan bola)
    dx = ex - sx
    dy = ey - sy

    length = (dx**2 + dy**2) ** 0.5
    if length == 0:
        print("[-] Vektor arah nol, skip shot.")
        return None

    # Swipe mulai dari POSISI BOLA (sama seperti best_shot level 1)
    # Semakin jauh jarak swipe = semakin besar power
    # Pakai SWIPE_LENGTH besar agar power selalu maksimal
    SWIPE_LENGTH = 600
    norm_dx = dx / length
    norm_dy = dy / length

    swipe_start_x = sx
    swipe_start_y = sy
    # Swipe ke arah BERLAWANAN dari target (game mechanic: tarik mundur = tembak ke depan)
    swipe_end_x = int(sx - norm_dx * SWIPE_LENGTH)
    swipe_end_y = int(sy - norm_dy * SWIPE_LENGTH)

    # Clamp agar tidak keluar layar
    swipe_end_x = max(10, min(710, swipe_end_x))
    swipe_end_y = max(10, min(1590, swipe_end_y))

    # duration_ms 1000ms sesuai best_shot level 1
    SWIPE_DURATION_MS = 1000

    print(f"[*] AI TARGET: ({ex},{ey}) | SWIPE: ({swipe_start_x},{swipe_start_y})->({swipe_end_x},{swipe_end_y}) dur:{SWIPE_DURATION_MS}ms")
    adb(f"shell input swipe {swipe_start_x} {swipe_start_y} {swipe_end_x} {swipe_end_y} {SWIPE_DURATION_MS}")
    time.sleep(1)

    return {"drop_x": shot_data.get('drop_x', sx), "drop_y": shot_data.get('drop_y', sy),
            "start_x": swipe_start_x, "start_y": swipe_start_y,
            "end_x": swipe_end_x, "end_y": swipe_end_y,
            "duration_ms": SWIPE_DURATION_MS, "reverse": False}

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

        print(f"\n=== MENGANALISA TEMBAKAN LEVEL {current_level} DENGAN AI (GROQ) ===")
        print("[*] MENGAMBIL SCREENSHOT MEJA: Kondisi bola sudah mendarat anteng...")
        capture_screen(SCREENSHOT_PATH)
        apply_grid_overlay(SCREENSHOT_PATH, GRID_SCREENSHOT_PATH)
        fails = json.load(open(FAILED_LOG_FILE, 'r')).get(str(current_level), []) if os.path.exists(FAILED_LOG_FILE) else []

        shot_plan = get_shot_from_ai(current_level, LEVEL_STRATEGY.get(current_level, ""), fails)
        if not shot_plan:
            time.sleep(5)
            continue

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
            log_failed(current_level, shot_plan)
            recover_to_start()
            replay_to_level(current_level)

    export_macrodroid()

if __name__ == "__main__":
    main()
