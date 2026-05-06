import random


class MayinMantigi:


    def __init__(self, satir, sutun, mayin_sayisi):
        self.satir = satir
        self.sutun = sutun
        self.mayin_sayisi = mayin_sayisi
        self.izgara = []  # 0: Boş, -1: Mayın, 1-8: Komşu sayısı
        self.mayin_konumlari = set()
        self.hazirla()
        self.bayrakli_hucreler = set()  # Bayrak konulan koordinatları tutar

    def bayrak_degistir(self, r, c):
        if (r, c) in self.bayrakli_hucreler:
            self.bayrakli_hucreler.remove((r, c))
            return False  # Bayrak kaldırıldı
        else:
            self.bayrakli_hucreler.add((r, c))
            return True  # Bayrak eklendi

    def hazirla(self):
        # Önce içi 0 dolu bir ızgara oluştur
        self.izgara = [[0 for _ in range(self.sutun)] for _ in range(self.satir)]

        # Rastgele mayın yerleştir
        sayac = 0
        while sayac < self.mayin_sayisi:
            r = random.randint(0, self.satir - 1)
            c = random.randint(0, self.sutun - 1)
            if (r, c) not in self.mayin_konumlari:
                self.izgara[r][c] = -1
                self.mayin_konumlari.add((r, c))
                sayac += 1

        # Komşu mayın sayılarını hesapla
        for r, c in self.mayin_konumlari:
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < self.satir and 0 <= nc < self.sutun and self.izgara[nr][nc] != -1:
                        self.izgara[nr][nc] += 1

    def bos_hucreleri_genislet(self, satir, sutun, ziyaret_edilen=None):
        if ziyaret_edilen is None:
            ziyaret_edilen = set()

        # Koordinat sınır dışıysa veya zaten ziyaret edildiyse dur
        if (satir, sutun) in ziyaret_edilen or not (0 <= satir < self.satir and 0 <= sutun < self.sutun):
            return ziyaret_edilen

        ziyaret_edilen.add((satir, sutun))

        # Eğer hücre boşsa (değeri 0 ise), komşularına bak
        if self.izgara[satir][sutun] == 0:
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    self.bos_hucreleri_genislet(satir + dr, sutun + dc, ziyaret_edilen)

        return ziyaret_edilen
