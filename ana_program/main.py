import cv2
import torch
import numpy as np
import serial
import time
import segmentation_models_pytorch as smp

# --- 1. MODEL VE DONANIM HAZIRLIĞI ---
CIHAZ = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Kullanılan donanım: {CIHAZ}")

# Senin mimarini kuruyor
try:
    model = smp.Unet(encoder_name="resnet18", encoder_weights=None, in_channels=3, classes=1)
    # Senin en iyi ağırlığını yüklüyor
    model.load_state_dict(torch.load("unet_model.pth", map_location=CIHAZ))
    model.to(CIHAZ)
    model.eval()  # Modeli tahmin moduna alıyor
    print("Model başarıyla yüklendi!")
except Exception as e:
    print(f"Model yüklenirken hata oluştu: {e}")
    exit()

# Arduino bağlantısı
try:
    arduino = serial.Serial(port='/dev/ttyUSB0', baudrate=9600, timeout=0.1)
    time.sleep(2)
    arduino = None
except Exception as e:
    print(f"Arduino bağlantı hatası: {e}")
    arduino = None

TOLERANCE = 50


# --- 2. YARDIMCI FONKSİYONLAR ---
def tahmin_et(kamera_karesi):
    # Ön İşleme (Senin eğitimde yaptığının aynısı)
    resim = cv2.cvtColor(kamera_karesi, cv2.COLOR_BGR2RGB)
    resim = cv2.resize(resim, (640, 640))
    resim = resim.transpose(2, 0, 1).astype('float32') / 255.0

    # PyTorch tensörüne çevirip batch boyutu ekleme (1, 3, 640, 640)
    tensor = torch.from_numpy(resim).unsqueeze(0).to(CIHAZ)

    # Modeli Çalıştırma (Forward işlemi)
    with torch.no_grad():  # Gradyan hesaplamayı kapatır, aracı hızlandırır
        cikti = model(tensor)
        # Çıktıyı 0 ile 1 arasına sıkıştırıp 0.5 eşik değeri uygula
        maske = torch.sigmoid(cikti) > 0.5

        # Maskeyi tekrar OpenCV'nin anlayacağı (640, 640) numpy formatına geri çevir
    maske_numpy = maske.squeeze().cpu().numpy().astype(np.uint8) * 255

    return maske_numpy  # Bu sana siyah/beyaz yol maskesini verir


def get_centroid(mask):
    # Maskenin ağırlık merkezini (yolun ortasını) bulur
    M = cv2.moments(mask)
    if M["m00"] != 0:
        return int(M["m10"] / M["m00"])
    return None


# --- 3. ANA DÖNGÜ (ALGI-KARAR-EYLEM) ---
# Bilgisayarın kamerasını başlat
#!!!!!!!! cap = cv2.VideoCapture(0)

# İP WEBCAM
ip_kamera_url = "http://192.168.1.55:8080/video"
cap = cv2.VideoCapture(ip_kamera_url)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Kameranın gerçek boyutlarını alıyoruz (Çizim ve doğru hata hesabı için)
    original_height, original_width = frame.shape[:2]

    # Modele kameradan gelen görüntüyü verip maskeyi alıyoruz
    mask_640 = tahmin_et(frame)

    # DİKKAT: Hesaplamaların doğru olması için 640x640 olan maskeyi,
    # tekrar orijinal kamera boyutuna (örn: 1920x1080 veya 640x480) döndürüyoruz.
    mask_resized = cv2.resize(mask_640, (original_width, original_height), interpolation=cv2.INTER_NEAREST)

    # Yolun merkezi ve ekranın merkezi
    road_center_x = get_centroid(mask_resized)
    img_center_x = original_width // 2

    if road_center_x is not None:
        # Hata hesabı: Yol sağda mı kaldı solda mı?
        error = road_center_x - img_center_x

        if abs(error) <= TOLERANCE:
            cmd = 'S'  # Düz git
        elif error > TOLERANCE:
            cmd = 'R'  # Sağ (Yolun merkezi ekranın sağında kalıyor)
        else:
            cmd = 'L'  # Sol (Yolun merkezi ekranın solunda kalıyor)

        # --- GÖRSEL HATA AYIKLAMA (Ekrana çizdirme) ---
        # Yolun merkezini kırmızı, Kameranın merkezini mavi nokta olarak gösterelim
        cv2.circle(frame, (road_center_x, original_height // 2), 10, (0, 0, 255), -1)
        cv2.circle(frame, (img_center_x, original_height // 2), 10, (255, 0, 0), -1)
        cv2.putText(frame, f"Hata: {error} - Komut: {cmd}", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    else:
        cmd = 'B'  # Yol bulunamadı, dur!
        cv2.putText(frame, "Yol Bulunamadi! Komut: B", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # Komutu Arduino'ya gönder
    if arduino:
        arduino.write(cmd.encode())

    # Ekrana sonuçları bas
    cv2.imshow('Kamera', frame)
    cv2.imshow('U-Net Maske', mask_resized)

    # 'q' tuşuna basıldığında döngüyü kır ve çık
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()