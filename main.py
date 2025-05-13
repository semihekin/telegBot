import telebot
#import gspread
#from oauth2client.service_account import ServiceAccountCredentials
import time
import datetime
import requests
import cv2
import numpy as np
from io import BytesIO
from PIL import Image
import pandas as pd
import csv

BOT_TOKEN = "7615666093:AAEEIgQB9zoVOO3F88SjYueSJ5yyopl5cpI"
SHEET_ID = "1rr8uOk0boXCYT3fSy_qROAeKnupuZfs4PxJO3dsGXJQ"
SEMIH_ID = 457314997

allowed_user_ids = [457314997, 7802889920, 7987047737, 1249056982, 7883584655, 7702179083]
detayli_izinli_ids = [457314997, 7802889920, 7987047737]

#scope = [
#    "https://spreadsheets.google.com/feeds",
#    "https://www.googleapis.com/auth/spreadsheets",
#    "https://www.googleapis.com/auth/drive"
#]
#creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
#client = gspread.authorize(creds)
#sheet = client.open_by_key(SHEET_ID).worksheet("Sayfa1")
#f"⛔ Merhaba @{kullanici_adi}, Ürünlerimiz Hakkında Bilgi Almak İçin Bizimle İrtibata Geçebilirsiniz !."

bot = telebot.TeleBot(BOT_TOKEN)
bekleyen_onaylar = {}

@bot.message_handler(commands=["start"])
def start(message):
    try:
        kullanici_id = message.from_user.id
        kullanici_adi = message.from_user.username or message.from_user.first_name
        kod = message.text.replace("/start", "").replace("=", " ").strip()
        zaman = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

        if kullanici_id not in allowed_user_ids:
            # Kullanıcıya bilgi ver
            bot.send_message(
                kullanici_id,
                f"⛔ Merhaba @{kullanici_adi}, Ürünlerimiz Hakkında Bilgi Almak İçin Bizimle İrtibata Geçebilirsiniz !."
            )

            # Size bilgi gönder
            bot.send_message(
                SEMIH_ID,
                f"🚨 *Yetkisiz Erişim Tespiti!*\n"
                f"Kullanıcı: @{kullanici_adi} ({kullanici_id})\n"
                f"Tarih: {zaman}\n"
                f"Giriş Denemesi: `{kod}`",
                parse_mode="Markdown"
            )
            return

        if kod:
            message.text = kod
            cevapla(message)

            try:
                if message.chat.type in ["group", "supergroup"]:
                    bot.delete_message(message.chat.id, message.message_id)
            except:
                pass
        else:
            bot.send_message(message.chat.id, "👋 Hoş geldiniz! QR kod verisi bulunamadı.")
    except Exception as e:
        bot.send_message(message.chat.id, f"🚫 Hata oluştu: {e}")

# ONAY Fonksiyonu
@bot.message_handler(commands=["onay"])
def onayla(message):
    try:
        kod = message.text[6:].strip().upper()
        if message.from_user.id != SEMIH_ID:
            return

        if kod not in bekleyen_onaylar:
            bot.send_message(message.chat.id,
                             f"⚠️ Bekleyen onay bulunamadı: {kod}")
            return

        yeni_fiyat = bekleyen_onaylar.pop(kod)
        with open("veri.csv", encoding="ISO-8859-9", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            veriler = list(reader)
            lines = f.readlines()

        for i, line in enumerate(lines[1:], start=2):
            satir = line.strip().split(",")
            if satir and satir[0].strip().lower() == kod.lower():
                satir[3] = f"{yeni_fiyat} $"  # D sütunu (4. sütun)
                satir[4] = datetime.datetime.now().strftime("%d.%m.%y")  # E sütunu (5. sütun)
                lines[i-1] = ",".join(satir) + "\n"
                with open("veri.csv", newline='', encoding='windows-1254') as f:
                    f_w.writelines(lines)
                bot.send_message(
                    message.chat.id,
                    f"✅ {kod} fiyatı güncellendi: {yeni_fiyat} $")
                return

        bot.send_message(message.chat.id,
                         f"❌ {kod} sistemde bulunamadı.")

    except Exception as e:
        bot.send_message(message.chat.id, f"🚫 Hata oluştu: {e}")

# /kimim komutu
@bot.message_handler(commands=["kimim"])
def kimim(message):
    bot.reply_to(message, f"Sizin kullanıcı ID’niz: `{message.from_user.id}`", parse_mode="Markdown")


# Yeni SATIŞ komutu: satış-angora-semih-3,60
@bot.message_handler(func=lambda message: message.text.lower().startswith("satış "))
def satis_ekle(message):
    if message.from_user.id not in allowed_user_ids:
        bot.send_message(message.chat.id, "⛔ *YETKİSİZ İŞLEM*", parse_mode="Markdown")
        return

    try:
        parcalar = message.text.strip().split()

        if len(parcalar) != 4:
            bot.send_message(
                message.chat.id,
                "❗️ Hatalı komut. Doğru kullanım:\n`satış KOD MÜŞTERİ FİYAT`",
                parse_mode="Markdown")
            return

        _, kod, musteri, fiyat = parcalar
        kod = kod.strip().upper()
        yeni_kayit = f"{musteri} - {fiyat}"

        with open("veri.csv", encoding="ISO-8859-9", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            veriler = list(reader)
            lines = f.readlines()

        for i, line in enumerate(lines):
            satir = line.strip().split(",")
            if len(satir) >= 1 and satir[0].strip().upper() == kod:
                for j in range(10, len(satir)):
                    if satir[j].strip() == "":
                        satir[j] = yeni_kayit
                        lines[i] = ",".join(satir) + "\n"
                        with open("veri.csv", newline='', encoding='windows-1254') as f:
                            fw.writelines(lines)
                        bot.send_message(
                            message.chat.id,
                            f"✅ Kaydedildi: `{kod}` satırına → {yeni_kayit}",
                            parse_mode="Markdown")
                        return
                bot.send_message(message.chat.id, "⚠️ Tüm satış alanları dolu.", parse_mode="Markdown")
                return

        bot.send_message(message.chat.id, f"❌ *{kod}* kodu bulunamadı.", parse_mode="Markdown")

    except Exception as e:
        bot.send_message(message.chat.id, f"🚫 Hata oluştu: `{str(e)}`", parse_mode="Markdown")


# ➕ GİRİŞ komutu
@bot.message_handler(func=lambda message: message.text.lower().startswith("giriş "))
def giris_fonksiyonu(message):
    try:
        _, kod, fiyat = message.text.strip().split()
        kod = kod.strip().upper()
        fiyat = fiyat.replace(",", ".")

        with open("veri.csv", encoding="ISO-8859-9", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            veriler = list(reader)
            satirlar = f.readlines()

        for i, satir in enumerate(satirlar):
            hucreler = satir.strip().split(",")
            if len(hucreler) > 0 and hucreler[0].strip().lower() == kod.lower():
                mevcut_deger = hucreler[1].strip() if len(hucreler) > 1 else ""
                if mevcut_deger:
                    bot.send_message(
                        SEMIH_ID,
                        f"🔐 `{kod}` için daha önce `{mevcut_deger}` girilmiş. Yeni fiyat `{fiyat} $`.",
                        parse_mode="Markdown"
                    )
                    bekleyen_onaylar[kod] = fiyat
                    return

                hucreler[1] = f"{fiyat} $"
                hucreler[2] = datetime.datetime.now().strftime("%d.%m.%y")
                satirlar[i] = ",".join(hucreler) + "\n"

                with open("veri.csv", encoding="ISO-8859-9", newline="") as f:
                    reader = csv.DictReader(f, delimiter=";")
                    veriler = list(reader)
                    f.writelines(satirlar)

                bot.send_message(message.chat.id, f"✅ {kod} için fiyat girildi: {fiyat} $")
                return

        bot.send_message(message.chat.id, f"❌ {kod} bulunamadı.")
    except Exception as e:
        bot.send_message(message.chat.id, f"🚫 Hata oluştu: {e}")


# FİYAT komutu
@bot.message_handler(
    func=lambda message: message.text.lower().startswith("fiyat "))
def fiyat_sorgula(message):
    if message.from_user.id not in allowed_user_ids:
        bot.send_message(message.chat.id,
                         "⛔ *YETKİSİZ İŞLEM*",
                         parse_mode="Markdown")
        return

    kod = message.text[6:].strip().lower()

    try:
        with open("veri.csv", encoding="ISO-8859-9", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            veriler = list(reader)
            fiyatlar = []
            for satir in reader:
                if satir["kod"].strip().lower() == kod:
                    for harf in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                        kolon = f"A{harf}"
                        if kolon in satir:
                            deger = satir[kolon].strip()
                            if deger and "-" in deger:
                                fiyatlar.append(f"- {deger}")
                    if fiyatlar:
                        bot.send_message(message.chat.id,
                                         f"📦 *{kod.upper()}* satışları:\n" + "\n".join(fiyatlar),
                                         parse_mode="Markdown")
                    else:
                        bot.send_message(message.chat.id,
                                         f"ℹ️ *{kod.upper()}* için satış kaydı bulunamadı.",
                                         parse_mode="Markdown")
                    return
        bot.send_message(message.chat.id,
                         f"❌ *{kod.upper()}* kodu bulunamadı.",
                         parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"🚫 Hata oluştu: {e}")

# GÖRSEL komutu
@bot.message_handler(func=lambda message: message.text.lower().startswith("görsel "))
def gorsel_komutu(message):
    try:
        kod = message.text[7:].strip().upper()
        gorsel_gonder(message.chat.id, kod)
    except Exception as e:
        bot.send_message(message.chat.id, f"🚫 Görsel hatası: {e}")


def gorsel_gonder(chat_id, kod):
    try:
        dosya_yolu = f"image/{kod}.jpg"
        with open(dosya_yolu, "rb") as foto:
            bot.send_photo(chat_id, foto, caption=f"🖼️ {kod} görseli")
    except FileNotFoundError:
        bot.send_message(chat_id, f"❌ *{kod}* için görsel bulunamadı.", parse_mode="Markdown")
        
# Kod ya da detay komutu
@bot.message_handler(func=lambda message: not message.text.startswith("-"))
def cevapla(message):
    if message.from_user.id not in allowed_user_ids:
        bot.send_message(message.chat.id,
                         "⛔ *YETKİSİZ İŞLEM*",
                         parse_mode="Markdown")
        return

    metin = message.text.strip()
    detayli = False

    if metin.lower().startswith("detay "):
        detayli = True
        kodlar = metin[6:].strip().splitlines()
        if message.from_user.id not in detayli_izinli_ids:
            bot.send_message(message.chat.id,
                             "🔒 *DETAYLI BİLGİ* sadece yetkililere açıktır.",
                             parse_mode="Markdown")
            return
    else:
        kodlar = metin.splitlines()

    with open("veri.csv", encoding="ISO-8859-9", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        veriler = list(reader)

    for kod in kodlar:
        kod = kod.strip()
        bulundu = False

        for satir in veriler:
            if satir["kod"].strip().lower() == kod.lower():
                bulundu = True
                if detayli:
                    if message.chat.id != message.from_user.id:
                        try:
                            bot.delete_message(message.chat.id, message.message_id)
                        except Exception:
                            pass

                    atkilar = ""
                    for i in range(1, 9):
                        a_key = f"A{i}"
                        a_alt = f"A{i}{i}"
                        val = satir.get(a_key, "")
                        alt = satir.get(a_alt, "")
                        if val:
                            try:
                                if float(str(val).replace(",", ".")) != 0:
                                    atkilar += f"*A{i}*   :  `({alt})`    `{val}`\n"
                            except:
                                atkilar += f"*A{i}*   :  `({alt})`    `{val}`\n"

                    p_list = ""
                    for i in range(1, 11):
                        p_key = f"P{i}"
                        p_alt = f"P{i}F"
                        p_alk = f"P{i}B"
                        val = satir.get(p_key, "")
                        alt = satir.get(p_alt, "")
                        alk = satir.get(p_alk, "")
                        if val:
                            try:
                                if float(str(val).replace(",", ".")) != 0:
                                    p_list += f"*P{i}*   :  `{alt.rjust(8)}`  `{alk.rjust(8)}`  `  {val}`\n"
                            except:
                                p_list += f"*P{i}*   :  `{alt.rjust(8)}`  `{alk.rjust(8)}`  `  {val}`\n"

                    mesaj = (
                        f"*{kod.upper():<20}*`{satir.get('tarih', '?'):>20}`\n"
                        f"              *{satir.get('deger', '?')}*    ||    {satir.get('en', '?')}    ||    {satir.get('gr', '?')}\n"
                        f"              `{satir.get('Comp', '-')}`\n"
                        f"\n"
                        f"*ÇÖZGÜ*   :  {satir.get('cip', '-')}\n"
                        f"\n"
                        f"*ATKI*    :  {satir.get('cm', '?'):>60}\n"
                        f"{atkilar}"
                        f"\n"
                        f"*PROSES*  : {satir.get('PÇ', '-'):>50}\n"
                        f"{p_list}"
                    )

                    bot.send_message(message.from_user.id,
                                     mesaj,
                                     parse_mode="Markdown")
                    return

                else:
                    mesaj = (
                        f"*{kod.upper():<20}*`{satir.get('tarih', '?'):>20}`\n"
                        f"              *{satir.get('deger', '?')}*    ||    {satir.get('en', '?')}    ||    {satir.get('gr', '?')}\n"
                        #f"{satir.get('en', '?')}   ||   {satir.get('gr', '?')}   ||   *{satir.get('deger', '?')}*   ||   {satir.get('tarih', '?')}\n"
                        f"              `{satir.get('Comp', '-')}`\n"
                    )
                    bot.send_message(message.chat.id, mesaj, parse_mode="Markdown")
                    break

        if not bulundu:
            bot.send_message(message.chat.id, f"❌ {kod.upper()} bulunamadı.")


# Botu başlat
bot.polling(none_stop=True)

# Replit’te botun kapanmaması için
while True:
    time.sleep(60)
