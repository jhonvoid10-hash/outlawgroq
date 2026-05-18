import cv2
import subprocess
import os

SCALE_PERCENT = 40 

def adb(cmd):
    return subprocess.run(f"adb {cmd}", shell=True, capture_output=True, text=True).stdout.strip()

def capture_screen(filename="temp_crop_screen.png"):
    print("\n[*] Mengambil screenshot dari layar HP...")
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

    print(f"\n=========================================")
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
    
    input("\n[TUGAS 1] Buka halaman di HP yang ada tombol 'PLAY SOLO'. Tekan ENTER jika sudah siap...")
    screen_1 = capture_screen()
    crop_interactive(screen_1, "PLAY SOLO", "tpl_play_solo.png")
    
    input("\n[TUGAS 2] Buka halaman di HP yang ada tombol 'CLOSE (X)'. Tekan ENTER jika sudah siap...")
    screen_2 = capture_screen()
    crop_interactive(screen_2, "CLOSE (X)", "tpl_close.png")
    
    input("\n[TUGAS 3] Buat agar muncul popup 'YES' di layar HP. Tekan ENTER jika sudah siap...")
    screen_3 = capture_screen()
    crop_interactive(screen_3, "YES CONFIRM", "tpl_yes.png")

    input("\n[TUGAS 4] Masuk ke game, lewati Level 1 sampai muncul tombol 'CONTINUE'. Tekan ENTER jika sudah siap...")
    screen_4 = capture_screen()
    crop_interactive(screen_4, "CONTINUE", "tpl_continue.png")

    if os.path.exists("temp_crop_screen.png"):
        os.remove("temp_crop_screen.png")
    print("\n[+] Selesai! Semua tombol sudah dipotong. Lanjut jalankan auto_master_billiard.py")

if __name__ == "__main__":
    main()