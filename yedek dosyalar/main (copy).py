import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import datetime
import requests
import cv2
import numpy as np
from io import BytesIO
from PIL import Image

BOT_TOKEN = "7615666093:AAEEIgQB9zoVOO3F88SjYueSJ5yyopl5cpI"
SHEET_ID = "1rr8uOk0boXCYT3fSy_qROAeKnupuZfs4PxJO3dsGXJQ"
SEMIH_ID = 457314997

allowed_user_ids = [457314997, 7802889920, 7987047737, 1249056982, 7883584655, 7702179083]
detayli_izinli_ids = [457314997, 7802889920, 7987047737]

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet("Sayfa1")

bot = telebot.TeleBot(BOT_TOKEN)
bekleyen_onaylar = {}

# QR Fonksiyonu
@bot.message_handler(commands=["start"])
def start(message):
    try:
        # /start=ANGORA formatını da destekle
        text = message.text.replace("/start", "").replace("=", " ").strip()
        if text:
            message.text = text  # komuttan gelen kalite kodunu mesaj gibi işleyelim
            cevapla(message)

            # Mesaj silme işlemi yalnızca özel sohbette çalışır, grupta izin gerekir
            try:
                if message.chat.type in ["group", "supergroup"]:
                    member = bot.get_chat_member(message.chat.id, bot.get_me().id)
                    if member.status in ["administrator", "creator"]:
                        bot.delete_message(message.chat.id, message.message_id)
                else:
                    # özel sohbetse silmeye gerek yok zaten görünmüyor
                    pass
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
        veriler = sheet.get_all_records()

        for i, satir in enumerate(veriler, start=2):
            if str(satir.get("kod", "")).strip().lower() == kod.lower():
                sheet.update_acell(f"D{i}", f"{yeni_fiyat} $")
                guncellenen = sheet.acell(f"D{i}").value
                if guncellenen != f"{yeni_fiyat} $":
                    bot.send_message(
                        message.chat.id,
                        f"⚠️ Güncelleme başarısız oldu. Lütfen manuel kontrol et."
                    )
                else:
                    sheet.update_acell(
                        f"E{i}",
                        datetime.datetime.now().strftime("%d.%m.%y"))
                    bot.send_message(
                        message.chat.id,
                        f"✅ {kod} fiyatı güncellendi: {yeni_fiyat} $")
                return
    except Exception as e:
        bot.send_message(message.chat.id, f"🚫 Hata oluştu: {e}")

# QR Okuma Fonksiyonu
@bot.message_handler(content_types=['photo'])
def qr_oku(message):
    if message.from_user.id not in allowed_user_ids:
        return
    try:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file = bot.download_file(file_info.file_path)

        img = Image.open(BytesIO(file)).convert('RGB')
        img_np = np.array(img)
        img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(img_cv)

        if data:
            message.text = data
            cevapla(message)
        else:
            bot.reply_to(message, "❌ QR kod okunamadı.")
    except Exception as e:
        bot.reply_to(message, f"🚫 Hata oluştu: {e}")

# /kimim komutu
@bot.message_handler(commands=["kimim"])
def kimim(message):
    bot.send_message(message.chat.id,
                     f"Sizin kullanıcı ID’niz: `{message.from_user.id}`",
                     parse_mode="Markdown")


# Yeni SATIŞ komutu: satış-angora-semih-3,60
@bot.message_handler(
    func=lambda message: message.text.lower().startswith("satış "))
def satis_ekle(message):
    if message.from_user.id not in allowed_user_ids:
        bot.send_message(message.chat.id,
                         "⛔ *YETKİSİZ İŞLEM*",
                         parse_mode="Markdown")
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
        kod = kod.strip().lower()
        yeni_kayit = f"{musteri} - {fiyat}"

        veriler = sheet.get_all_records()

        for i, satir in enumerate(veriler, start=2):
            kod_hucre = str(satir.get("kod", "")).strip().lower()
            if kod_hucre == kod:
                for harf in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                    kolon = f"SAT_{harf}"
                    if kolon not in satir or not satir[kolon]:
                        sheet.update_acell(f"{kolon}{i}", yeni_kayit)
                        bot.send_message(
                            message.chat.id,
                            f"✅ Kaydedildi: `{kolon}{i}` → {yeni_kayit}",
                            parse_mode="Markdown")
                        return
                bot.send_message(message.chat.id,
                                 "⚠️ Tüm satış alanları dolu.",
                                 parse_mode="Markdown")
                return

        bot.send_message(message.chat.id,
                         f"❌ *{kod.upper()}* kodu bulunamadı.",
                         parse_mode="Markdown")

    except Exception as e:
        bot.send_message(message.chat.id,
                         f"🚫 Hata oluştu: `{str(e)}`",
                         parse_mode="Markdown")


# ➕ GİRİŞ komutu
@bot.message_handler(
    func=lambda message: message.text.lower().startswith("giriş "))
def giris_fonksiyonu(message):
    try:
        _, kod, fiyat = message.text.strip().split()
        kod = kod.strip().upper()
        fiyat = fiyat.replace(",", ".")

        veriler = sheet.get_all_records()

        for i, satir in enumerate(veriler, start=2):
            if str(satir.get("kod", "")).lower() == kod.lower():
                mevcut_deger = str(satir.get("deger", "")).strip()
                if mevcut_deger:
                    bot.send_message(
                        SEMIH_ID,
                        f"🔐 `{kod}` için daha önce `{mevcut_deger}` girilmiş. Yeni fiyat `{fiyat} $`.",
                        parse_mode="Markdown")
                    bekleyen_onaylar[kod] = fiyat
                    return

                sheet.update_acell(f"B{i}", f"{fiyat} $")
                sheet.update_acell(
                    f"C{i}",
                    datetime.datetime.now().strftime("%d.%m.%y"))
                bot.send_message(message.chat.id,
                                 f"✅ {kod} için fiyat girildi: {fiyat} $")
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
    veriler = sheet.get_all_records()

    for satir in veriler:
        if str(satir["kod"]).lower() == kod:
            fiyatlar = []
            for harf in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                kolon = f"A{harf}"
                if kolon in satir:
                    deger = satir[kolon]
                    if deger and "-" in deger:
                        fiyatlar.append(f"- {deger}")
            if fiyatlar:
                bot.send_message(message.chat.id,
                                 f"📦 *{kod.upper()}* satışları:\n" +
                                 "\n".join(fiyatlar),
                                 parse_mode="Markdown")
            else:
                bot.send_message(
                    message.chat.id,
                    f"ℹ️ *{kod.upper()}* için satış kaydı bulunamadı.",
                    parse_mode="Markdown")
            return

    bot.send_message(message.chat.id,
                     f"❌ *{kod.upper()}* kodu bulunamadı.",
                     parse_mode="Markdown")


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

    veriler = sheet.get_all_records()

    for kod in kodlar:
        kod = kod.strip()
        bulundu = False

        for satir in veriler:
            if str(satir["kod"]).lower() == kod.lower():
                bulundu = True
                if detayli:
                    # Mesajı sil (isteğe bağlı)
                    if message.chat.id != message.from_user.id:
                        try:
                            bot.delete_message(message.chat.id,
                                               message.message_id)
                        except Exception:
                            pass

                    # Detaylı mesajı oluştur
                    atkilar = ""
                    for i in range(1, 9):
                        a_key = f"A{i}"
                        a_alt = f"A{i}{i}"
                        val = satir.get(a_key)
                        alt = satir.get(a_alt, "")
                        if val not in ("", None):
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
                        val = satir.get(p_key)
                        alt = satir.get(p_alt, "")
                        alk = satir.get(p_alk, "")
                        if val not in ("", None):
                            try:
                                if float(str(val).replace(",", ".")) != 0:
                                    p_list += f"*P{i}*   :  `{str(alt).rjust(8)}`  `{str(alk).rjust(8)}`  `  {val}`\n"
                            except:
                                p_list += f"*P{i}*   :  `{str(alt).rjust(8)}`  `{str(alk).rjust(8)}`  `  {val}`\n"

                    mesaj = (
                        f"*{kod.upper()}*\n"
                        f"{satir.get('en', '?')}   ||   {satir.get('gr', '?')}   ||   *{satir.get('deger', '?')}*   ||   {satir.get('tarih', '?')}\n\n"
                        f"*ÇÖZGÜ*   :  {satir.get('cip', '-')}\n"
                        f"\n"
                        f"*ATKI*    :  {satir.get('cm', '?'):>60}\n"
                        f"{atkilar}"
                        f"\n"
                        f"*PROSES*  : {satir.get('PÇ', '-'):>50}\n"
                        f"{p_list}"
                        #f"*TİP*     :  {satir.get('tip', '-')}"
                    )

                    # 🟢 Sadece özelden gönder
                    bot.send_message(message.from_user.id,
                                     mesaj,
                                     parse_mode="Markdown")
                    return

                else:
                    mesaj = (
                        f"*{kod.upper()}*\n"
                        f"{satir.get('en', '?')}   ||   {satir.get('gr', '?')}   ||   *{satir.get('deger', '?')}*   ||   {satir.get('tarih', '?')}"
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
