import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout,
                             QPushButton, QAction, QLabel, QHBoxLayout,
                             QVBoxLayout, QMessageBox, QInputDialog)
from PyQt5.QtCore import Qt, pyqtSignal
from logic import MayinMantigi  # Oyun algoritması
from database import db_hazirla, skor_kaydet, skorlari_getir  # Veritabanı işlemleri

# Modern Görsel Stil (QSS)
MODERN_STIL = """
    QMainWindow {
        background-color: #2c3e50;
    }
    QLabel {
        color: #ecf0f1;
        font-family: 'Segoe UI', Arial;
        font-size: 16px;
        font-weight: bold;
    }
    QPushButton {
        background-color: #34495e;
        border: 2px solid #2c3e50;
        border-radius: 6px;
        color: #ffffff;
        font-weight: bold;
        font-size: 14px;
    }
    QPushButton:hover {
        background-color: #4a69bd;
    }
    QPushButton:disabled {
        background-color: #bdc3c7;
        color: #2c3e50;
    }
"""


# Sağ tık desteği için özelleştirilmiş buton sınıfı
class HucreButonu(QPushButton):
    sag_tiklandi = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.sag_tiklandi.emit()
        else:
            super().mousePressEvent(event)


class AnaPencere(QMainWindow):
    def __init__(self):
        super().__init__()

        # 1. Oyun Ayarları
        self.satir_sayisi = 10
        self.sutun_sayisi = 10
        self.mayin_sayisi = 15
        self.butonlar = {}
        self.oyun_aktif = True

        # 2. Veritabanı ve Mantık Kurulumu[cite: 1]
        db_hazirla()
        self.mantik = MayinMantigi(self.satir_sayisi, self.sutun_sayisi, self.mayin_sayisi)

        # 3. Pencere Ayarları ve Stil[cite: 2]
        self.setWindowTitle("Tactical Sweeper v2.0")
        self.setGeometry(100, 100, 450, 520)
        self.setStyleSheet(MODERN_STIL)

        self.arayuz_hazirla()
        self.menu_olustur()

    def arayuz_hazirla(self):
        merkezi_widget = QWidget()
        self.setCentralWidget(merkezi_widget)
        ana_layout = QVBoxLayout()

        # Bilgi Paneli: Bomba Sayacı ve Skor Butonu[cite: 2]
        bilgi_paneli = QHBoxLayout()
        self.bomba_sayaci = QLabel(f"💣 Kalan: {self.mayin_sayisi}")

        self.skor_butonu = QPushButton("🏆 Skorlar")
        self.skor_butonu.setFixedSize(100, 35)
        self.skor_butonu.clicked.connect(self.skorlari_goster)

        bilgi_paneli.addWidget(self.bomba_sayaci)
        bilgi_paneli.addStretch()
        bilgi_paneli.addWidget(self.skor_butonu)

        # Oyun Izgarası[cite: 2]
        izgara_layout = QGridLayout()
        izgara_layout.setSpacing(2)

        for r in range(self.satir_sayisi):
            for c in range(self.sutun_sayisi):
                btn = HucreButonu("")
                btn.setFixedSize(40, 40)
                btn.clicked.connect(lambda checked, row=r, col=c: self.hucre_tiklandi(row, col))
                btn.sag_tiklandi.connect(lambda row=r, col=c: self.bayrak_koy(row, col))
                izgara_layout.addWidget(btn, r, c)
                self.butonlar[(r, c)] = btn

        ana_layout.addLayout(bilgi_paneli)
        ana_layout.addLayout(izgara_layout)
        merkezi_widget.setLayout(ana_layout)

        # Üst Panel Butonları
        self.yeni_oyun_butonu = QPushButton("🔄 Yeni Oyun")
        self.yeni_oyun_butonu.setFixedSize(110, 35)
        self.yeni_oyun_butonu.clicked.connect(self.sifirla)  # Sifirla metoduna bağla

        self.skor_butonu = QPushButton("🏆 Skorlar")
        self.skor_butonu.setFixedSize(100, 35)

        bilgi_paneli.addWidget(self.bomba_sayaci)
        bilgi_paneli.addStretch()
        bilgi_paneli.addWidget(self.yeni_oyun_butonu)  # Yeni butonu ekle
        bilgi_paneli.addWidget(self.skor_butonu)

    def menu_olustur(self):
        menubar = self.menuBar()
        oyun_menu = menubar.addMenu("Seçenekler")

        yeni_aksiyon = QAction("Yeniden Başlat", self)
        yeni_aksiyon.triggered.connect(self.sifirla)
        oyun_menu.addAction(yeni_aksiyon)

        cikis_aksiyon = QAction("Kapat", self)
        cikis_aksiyon.triggered.connect(self.close)
        oyun_menu.addAction(cikis_aksiyon)

    def hucre_tiklandi(self, r, c):
        if not self.oyun_aktif or (r, c) in self.mantik.bayrakli_hucreler:
            return

        deger = self.mantik.izgara[r][c]

        if deger == -1:  # Mayına basıldı[cite: 1, 2]
            self.oyun_bitir(False)
        elif deger == 0:  # Boş alan - Zincirleme açılma[cite: 2]
            acilecekler = self.mantik.bos_hucreleri_genislet(r, c)
            for row, col in acilecekler:
                self.hucreyi_guncelle(row, col)
        else:
            self.hucreyi_guncelle(r, c)

        self.kazanma_kontrol()

    def bayrak_koy(self, r, c):
        if not self.oyun_aktif or not self.butonlar[(r, c)].isEnabled():
            return

        is_bayrak = self.mantik.bayrak_degistir(r, c)
        btn = self.butonlar[(r, c)]

        if is_bayrak:
            btn.setText("🚩")
            btn.setStyleSheet("color: #e74c3c; font-size: 18px;")
        else:
            btn.setText("")
            btn.setStyleSheet("")

        kalan = self.mayin_sayisi - len(self.mantik.bayrakli_hucreler)
        self.bomba_sayaci.setText(f"💣 Kalan: {max(0, kalan)}")

    def hucreyi_guncelle(self, r, c):
        btn = self.butonlar[(r, c)]
        if not btn.isEnabled(): return

        deger = self.mantik.izgara[r][c]
        btn.setEnabled(False)

        if deger > 0:
            btn.setText(str(deger))
            renkler = {1: "#2980b9", 2: "#27ae60", 3: "#e67e22", 4: "#8e44ad"}
            btn.setStyleSheet(f"color: {renkler.get(deger, '#c0392b')}; border: none; background-color: #ecf0f1;")
        else:
            btn.setStyleSheet("background-color: #ecf0f1; border: none;")

    def kazanma_kontrol(self):
        acik_hucreler = sum(1 for btn in self.butonlar.values() if not btn.isEnabled())
        hedef = (self.satir_sayisi * self.sutun_sayisi) - self.mayin_sayisi
        if acik_hucreler == hedef:
            self.oyun_bitir(True)

    def oyun_bitir(self, kazandi):
        self.oyun_aktif = False
        mesaj = "Tebrikler! Kazandınız 🏆" if kazandi else "Güm! Kaybettiniz 💣"

        # --- FIX: Skor hesaplamasını butonları kapatmadan ÖNCE yapıyoruz ---
        # Sadece oyuncunun açtığı (zaten disabled olan) hücreleri sayar
        acik_hucre_sayisi = sum(1 for b in self.butonlar.values() if not b.isEnabled())
        skor = acik_hucre_sayisi * 10
        # ----------------------------------------------------------------

        # Şimdi görsel olarak tüm mayınları gösterip butonları kapatabiliriz
        for (r, c), btn in self.butonlar.items():
            if self.mantik.izgara[r][c] == -1:
                btn.setText("💣")
                btn.setStyleSheet("background-color: #e67e22;" if kazandi else "background-color: #e74c3c;")
            btn.setEnabled(False)  # Tüm butonlar şimdi kapanıyor

        # Skor Kaydı (Doğru skor değişkenini kullanıyoruz)
        isim, ok = QInputDialog.getText(self, "Oyun Bitti",
                                        f"{mesaj}\nSkorunuz: {skor}\nİsminizi girin:")
        if ok and isim:
            skor_kaydet(isim, skor, "Normal")
            self.skorlari_goster()


    def skorlari_goster(self):
        veriler = skorlari_getir()
        if not veriler:
            QMessageBox.information(self, "Skorlar", "Henüz kaydedilmiş skor yok.")
            return

        liste = "🏆 EN YÜKSEK SKORLAR 🏆\n\n"
        for i, (ad, puan, tarih) in enumerate(veriler[:10], 1):
            liste += f"{i}. {ad} - {puan} Puan ({tarih[:10]})\n"
        QMessageBox.information(self, "Liderlik Tablosu", liste)

    def sifirla(self):
        self.yeni_oyun = AnaPencere()
        self.yeni_oyun.show()
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pencere = AnaPencere()
    pencere.show()
    sys.exit(app.exec_())