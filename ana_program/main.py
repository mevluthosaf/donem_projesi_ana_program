import cv2
import torch
import numpy as np
import serial
import time
import segmentation_models_pytorch as smp

CIHAZ = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Kullanılan donanım: {CIHAZ}")

# U-Net modeli yükleme
try:
    model = smp.Unet(encoder_name="resnet18", encoder_weights=None, in_channels=3, classes=1)
    model.load_state_dict(torch.load("unet_model.pth", map_location=CIHAZ))
    model.to(CIHAZ)
    model.eval()  # Tahmin modu
    print("Model başarıyla yüklendi!")
except Exception as e:
    print(f"Model yüklenirken hata oluştu: {e}")
    exit()

# Arduino bağlantısı
try:
    print("Arduino'ya bağlanılıyor...")
    arduino = serial.Serial(port='/dev/ttyUSB0', baudrate=9600, timeout=0.1)
    time.sleep(2)  # Resetlenme süresi
    print("Arduino bağlantısı kuruldu!")
except Exception as e:
    print(f"Arduino bağlantı hatası: {e}")
    arduino = None

TOLERANCE = 50


# --- 2. YARDIMCI FONKSİYONLAR ---
def tahmin_et(kamera_karesi):
    resim = cv2.cvtColor(kamera_karesi, cv2.COLOR_BGR2RGB)
    resim = cv2.resize(resim, (640, 640))
    resim = resim.transpose(2, 0, 1).astype('float32') / 255.0

    tensor = torch.from_numpy(resim).unsqueeze(0).to(CIHAZ)

    with torch.no_grad():
        cikti = model(tensor)
        maske = torch.sigmoid(cikti) > 0.5

    maske_numpy = maske.squeeze().cpu().numpy().astype(np.uint8) * 255
    return maske_numpy


def get_centroid(mask):
    M = cv2.moments(mask)
    if M["m00"] != 0:
        return int(M["m10"] / M["m00"])
    return None


# --- 3. ANA DÖNGÜ ---
# USB WEBCAM BAĞLANTISI
# Raspberry Pi üzerindeki ilk USB kamera genelde 0 indeksini alır. Eğer harici bir kamera daha varsa 1 yapabilirsin.
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Görüntü biriktirmeyi kapatır

# Performans optimizasyonu için zaman değişkenleri
islem_araligi = 0.5  # Saniyede 2 kare işlemek için (1 / 2 = 0.5 saniye)
son_islem_zamani = time.time()

while cap.isOpened():
    # Kameradan her döngüde kareyi oku ki buffer dolsun ve görüntü gecikmesin (lag olmasın)
    ret, frame = cap.read()
    if not ret:
        break

    su_an = time.time()

    # Eğer son işlemden bu yana 0.5 saniye geçtiyse değerlendirmeyi yap
    if su_an - son_islem_zamani >= islem_araligi:
        son_islem_zamani = su_an

        original_height, original_width = frame.shape[:2]

        # Model değerlendirmesi (Yalnızca saniyede 2 kez çalışacak, işlemciyi rahatlatacak)
        mask_640 = tahmin_et(frame)
        mask_resized = cv2.resize(mask_640, (original_width, original_height), interpolation=cv2.INTER_NEAREST)

        road_center_x = get_centroid(mask_resized)
        img_center_x = original_width // 2

        if road_center_x is not None:
            error = road_center_x - img_center_x

            if abs(error) <= TOLERANCE:
                cmd = 'S'
            elif error > TOLERANCE:
                cmd = 'R'
            else:
                cmd = 'L'

            cv2.circle(frame, (road_center_x, original_height // 2), 10, (0, 0, 255), -1)
            cv2.circle(frame, (img_center_x, original_height // 2), 10, (255, 0, 0), -1)
            cv2.putText(frame, f"Hata: {error} - Komut: {cmd}", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        else:
            cmd = 'B'
            cv2.putText(frame, "Yol Bulunamadi! Komut: B", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Arduino'ya saniyede 2 kez komut gönderimi
        if arduino:
            arduino.write(cmd.encode())
            print(f"Komut Gitti: {cmd}")
        else:
            print("DİKKAT: Arduino bağlantısı yok, komut gönderilemedi!")

        # Görüntü pencerelerini de sadece kare işlendiğinde güncelleyerek ekstra performanstan tasarruf ediyoruz
        cv2.imshow('Kamera', frame)
        cv2.imshow('U-Net Maske', mask_resized)

    # Çıkış kontrolü her döngüde çalışır, 'q' tuşu anında tepki verir
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()