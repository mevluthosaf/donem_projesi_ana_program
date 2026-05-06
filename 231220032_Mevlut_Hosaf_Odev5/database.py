import sqlite3

def db_hazirla():
    # scores.db adında bir veritabanı dosyası oluşturur veya bağlanır[cite: 1]
    conn = sqlite3.connect('scores.db')
    cursor = conn.cursor()

    # Skor tablosunu oluşturma (Eğer yoksa)[cite: 1]
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS liderlik_tablosu
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       oyuncu_adi
                       TEXT
                       NOT
                       NULL,
                       skor
                       INTEGER
                       NOT
                       NULL,
                       zorluk
                       TEXT,
                       tarih
                       DATETIME
                       DEFAULT
                       CURRENT_TIMESTAMP
                   )
                   ''')
    conn.commit()
    conn.close()


def skor_kaydet(isim, puan, zorluk):
    conn = sqlite3.connect('scores.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO liderlik_tablosu (oyuncu_adi, skor, zorluk) VALUES (?, ?, ?)",
                   (isim, puan, zorluk))
    conn.commit()
    conn.close()

def skorlari_getir():
    conn = sqlite3.connect('scores.db')
    cursor = conn.cursor()
    # Skorları azalan sırayla (DESC) getiriyoruz
    cursor.execute("SELECT oyuncu_adi, skor, tarih FROM liderlik_tablosu ORDER BY skor DESC")
    veriler = cursor.fetchall()
    conn.close()
    return veriler