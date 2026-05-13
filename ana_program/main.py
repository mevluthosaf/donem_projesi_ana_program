import cv2
import torch
import numpy as np
import serial
import time
import segmentation_models_pytorch as smp

# Donanım ayarı
CIHAZ = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Kullanılan donanım: {CIHAZ}")

# Model yükleme
try:
    model = smp.Unet(encoder_name="resnet18", encoder_weights=None, in_channels=3, classes=1)
    model.load_state_dict(torch.load("unet_model.pth", map_location=CIHAZ))
    model.to(CIHAZ)
    model.eval()
    print("Model başarıyla yüklendi!")
except Exception as e:
    print(f"Model yükleme hatası: {e}")
    exit()

# Arduino bağlantısı
try:
    arduino = serial.Serial(port='/dev/ttyUSB0', baudrate=9600, timeout=0.1)
    time.sleep(2)
    print("Arduino bağlantısı kuruldu!")
except Exception as e:
    print(f"Arduino bağlantı hatası: {e}")
    arduino = None

TOLERANCE = 50


def tahmin_et(kamera_karesi):
    resim = cv2.cvtColor(kamera_karesi, cv2.COLOR_BGR2RGB)
    resim = cv2.resize(resim, (640, 640))
    resim = resim.transpose(2, 0, 1).astype('float32') / 255.0
    tensor = torch.from_numpy(resim).unsqueeze(0).to(CIHAZ)
    with torch.no_grad():
        cikti = model(tensor)
        maske = torch.sigmoid(cikti) > 0.5
    return maske.squeeze().cpu().numpy().astype(np.uint8) * 255


def get_centroid(mask):
    M = cv2.moments(mask)
    if M["m00"] != 0:
        return int(M["m10"] / M["m00"])
    return None


# USB Kamera Başlatma
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

islem_araligi = 0.5  # 2 FPS için 0.5 saniye bekleme
son_islem_zamani = time.time()

try:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        su_an = time.time()

        # Performans: Saniyede sadece 2 kareyi derin öğrenme modeline sok
        if su_an - son_islem_zamani >= islem_araligi:
            son_islem_zamani = su_an

            orig_h, orig_w = frame.shape[:2]
            mask_640 = tahmin_et(frame)
            mask_resized = cv2.resize(mask_640, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)

            road_center_x = get_centroid(mask_resized)
            img_center_x = orig_w // 2

            if road_center_x is not None:
                error = road_center_x - img_center_x
                cmd = 'S' if abs(error) <= TOLERANCE else ('R' if error > TOLERANCE else 'L')

                # Ekrana çizim işlemleri
                cv2.circle(frame, (road_center_x, orig_h // 2), 10, (0, 0, 255), -1)
                cv2.circle(frame, (img_center_x, orig_h // 2), 10, (255, 0, 0), -1)
                cv2.putText(frame, f"Komut: {cmd}", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            else:
                cmd = 'B'
                cv2.putText(frame, "Yol Yok!", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            if arduino:
                arduino.write(cmd.encode())

            # Fiziksel ekranda görüntüle
            cv2.imshow('Otonom Arac Gorusu', frame)
            cv2.imshow('Yol Maskesi', mask_resized)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("Durduruldu.")
finally:
    cap.release()
    cv2.destroyAllWindows()
    if arduino: arduino.close()