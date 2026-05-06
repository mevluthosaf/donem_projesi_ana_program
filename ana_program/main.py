import cv2
import torch
import torch.nn as nn
import torchvision.transforms as transforms
import numpy as np
import serial
import time


# --- 1. MODEL TANIMLAMA ---
# DİKKAT: unet_model.pth dosyasını eğitirken kullandığın model sınıfını buraya eklemelisin.
# Örnek bir kalıp:
class SimpleUNet(nn.Module):
    pass  # Kendi model mimarini buraya yapıştır. Eğer dosyan tüm modeli kapsıyorsa bu sınıfa gerek kalmayabilir.


# Modeli yükle (Bilgisayarında ekran kartı varsa onu kullanır, yoksa işlemciye geçer)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Kullanılan donanım: {device}")

try:
    # Eğer model dosyan sadece ağırlıkları değil tüm mimariyi içeriyorsa bu şekilde yüklenir:
    model = torch.load('unet_model.pth', map_location=device)
    model.eval()
    print("Model başarıyla yüklendi!")
except Exception as e:
    print(f"Model yüklenirken hata oluştu: {e}")
    exit()

# --- 2. DONANIM VE ÖN İŞLEME HAZIRLIĞI ---
# DİKKAT: Bilgisayarda Arduino portu genellikle COM3, COM4 (Windows) veya /dev/tty.usbmodem... (Mac) şeklindedir.
try:
    # arduino = serial.Serial(port='COM3', baudrate=9600, timeout=0.1) 
    # time.sleep(2)
    arduino = None  # Şimdilik PC'de test ederken Arduino bağlı değilse None bırakıyoruz
except:
    arduino = None

transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((640, 640)),  # Raporundaki boyuta uygun
    transforms.ToTensor(),
])

# Bilgisayarın dahili kamerasını başlat
cap = cv2.VideoCapture(0)
TOLERANCE = 50


def get_centroid(mask):
    M = cv2.moments(mask)
    if M["m00"] != 0:
        return int(M["m10"] / M["m00"])
    return None


# --- 3. ANA DÖNGÜ (ALGI-KARAR-EYLEM) ---
while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    input_tensor = transform(frame).unsqueeze(0).to(device)

    with torch.no_grad():
        output = model(input_tensor)
        pred = torch.sigmoid(output) > 0.5
        mask = pred.squeeze().cpu().numpy().astype(np.uint8) * 255

    road_center_x = get_centroid(mask)
    img_center_x = frame.shape[1] // 2

    if road_center_x is not None:
        error = road_center_x - img_center_x

        if abs(error) <= TOLERANCE:
            cmd = 'S'  # Düz
        elif error > TOLERANCE:
            cmd = 'R'  # Sağ
        else:
            cmd = 'L'  # Sol
    else:
        cmd = 'B'  # Dur

    if arduino:
        arduino.write(cmd.encode())

    # Ekrana hem orijinal görüntüyü hem de U-Net'in çıkardığı maskeyi verelim
    cv2.imshow('Kamera', frame)
    cv2.imshow('U-Net Maske', mask)

    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()