# Oylik va Rasxod Hisob-kitob Boti

Bu bot orqali siz quyidagilarni qila olasiz:
- Xodimlarga oylik belgilash va to'lovlarni qadam-baqadam kiritish (boshida 100$, o'rtasida 300$, qolganini oxirida)
- Qancha to'langan va qancha qolganini avtomatik hisoblash
- Kategoriyalar bo'yicha xarajatlarni kiritish (arenda, do'kon va boshqalar — o'zingiz qo'shishingiz mumkin)
- Valyuta ayirboshlash (so'm ↔ dollar) yozuvlarini saqlash
- Oy bo'yicha umumiy statistikani bir tugma bilan ko'rish

## 1-qadam: Bot tokenini olish

1. Telegramda **@BotFather** ga yozing
2. `/newbot` buyrug'ini yuboring
3. Botga nom va username bering (username "bot" bilan tugashi kerak, masalan `oylik_hisob_bot`)
4. BotFather sizga TOKEN beradi — masalan: `123456789:ABCdefGhIJKlmNoPQRstuVwxYZ`
5. Shu tokenni saqlab qo'ying

## 2-qadam: O'z Telegram ID'ingizni bilish (ixtiyoriy, lekin tavsiya etiladi)

Faqat o'zingiz botdan foydalanishni xohlasangiz (boshqalar kira olmasin):
1. Telegramda **@userinfobot** ga yozing
2. U sizga ID raqamingizni beradi (masalan: `123456789`)
3. `bot.py` faylida `ALLOWED_USER_IDS = set()` qatorini topib, shunday qiling:
   ```python
   ALLOWED_USER_IDS = {123456789}  # o'z ID'ingizni shu yerga yozing
   ```

## 3-qadam: Render.com'da 24/7 ishlatish (bepul)

Bu usul bilan bot doim ishlaydi — telefon yoki kompyuteringiz o'chiq bo'lsa ham.

### A) GitHub'ga yuklash

1. [github.com](https://github.com) da bepul akkaunt oching (agar yo'q bo'lsa)
2. Yangi repository (loyiha) yarating, masalan nomi: `oylik-bot`
3. Shu papkadagi barcha fayllarni (`bot.py`, `database.py`, `requirements.txt`, `render.yaml`, `.gitignore`) shu repository'ga yuklang. Buni GitHub saytida "Add file → Upload files" tugmasi orqali, fayllarni shunchaki tortib tashlab qilishingiz mumkin — Git buyruqlarini bilish shart emas.

### B) Render.com'da deploy qilish

1. [render.com](https://render.com) saytida bepul akkaunt oching (GitHub orqali kirish qulay)
2. Dashboard'da **New +** → **Background Worker** tanlang
3. GitHub repository'ngizni ulang (`oylik-bot`)
4. Render avtomatik `render.yaml` faylini topadi va sozlamalarni o'zi to'ldiradi:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python bot.py`
5. **Environment Variables** bo'limida qo'shing:
   - Key: `BOT_TOKEN`, Value: BotFather'dan olgan tokeningiz
6. **Create Background Worker** tugmasini bosing

Bir necha daqiqadan keyin bot ishga tushadi. Loglarni Render dashboard'ida "Logs" bo'limida ko'rish mumkin — agar xatolik bo'lsa, shu yerda chiqadi.

### C) Ma'lumotlar yo'qolib qolmasligi uchun (Persistent Disk)

Render bepul tarifida kod har safar qayta ishga tushganda (masalan yangilanish kiritganda) fayllar tozalanadi — bu SQLite bazangiz ham o'chib ketishi degani. Buning oldini olish uchun:

1. Render dashboard'ida bot xizmatingizni oching
2. **Disks** bo'limiga o'ting → **Add Disk**
3. Mount Path: `/data` deb yozing, hajmi 1GB (bepul tarifda ham mavjud)
4. **Environment Variables** ga yana bitta o'zgaruvchi qo'shing:
   - Key: `DB_PATH`, Value: `/data/bot_data.db`
5. Saqlang — bot qayta ishga tushadi va endi ma'lumotlar doimiy diskda saqlanadi

Eslatma: Render'ning bepul tarifida ba'zan disk funksiyasi cheklangan bo'lishi mumkin (tarifga qarab). Agar disk qo'shilmasa, muqobil sifatida Render'ning narxlangan ($7/oy) tarifiga o'tish yoki ma'lumotlarni vaqti-vaqti bilan qo'lda zaxira nusxalashni tavsiya qilamiz.

## 4-qadam: Kompyuteringizda ishga tushirish (lokal test uchun)

Python 3.10+ kerak. Terminal/CMD oching:

```bash
# Loyiha papkasiga kiring
cd oylik_bot

# Kerakli kutubxonalarni o'rnating
pip install -r requirements.txt

# Tokenni muhit o'zgaruvchisiga o'rnating
# Windows (CMD):
set BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRstuVwxYZ
# Windows (PowerShell):
$env:BOT_TOKEN="123456789:ABCdefGhIJKlmNoPQRstuVwxYZ"
# Mac/Linux:
export BOT_TOKEN="123456789:ABCdefGhIJKlmNoPQRstuVwxYZ"

# Botni ishga tushiring
python bot.py
```

Bot ishga tushgach, Telegramda botingizni topib `/start` deb yozing.

## Botdan foydalanish

**Oyliklar bo'limi:**
- "Xodim qo'shish" — ism va oylik summasini (USD) kiritasiz
- "To'lov kiritish" — xodimni tanlaysiz, summani va valyutani kiritasiz (so'mda kiritsangiz, USD ekvivalentini so'raydi, joriy kursda hisoblab kiritasiz)
- "Xodimlar holati" — har bir xodim bo'yicha to'langan/qolgan summa va umumiy yig'indi

**Rasxodlar bo'limi:**
- "Xarajat kiritish" — kategoriya tanlaysiz (arenda, do'kon va h.k.), summa, valyuta va izoh kiritasiz
- "Kategoriya qo'shish" — yangi xarajat turi qo'shish (masalan "Yoqilg'i", "Reklama")

**Kurs ayirboshlash bo'limi:**
- Qaysi valyutani berganingizni va evaziga qancha olganingizni kiritasiz — bot avtomatik kursni hisoblab saqlaydi

**Statistika bo'limi:**
- Joriy oy bo'yicha: jami oyliklar, to'langan/qolgan summa, kategoriya bo'yicha xarajatlar, barcha ayirboshlash amallari

Har qanday vaqtda `/cancel` yozsangiz, joriy amal bekor bo'ladi va asosiy menyuga qaytasiz.

## Muhim eslatmalar

- Ma'lumotlar SQLite faylida saqlanadi. Render'da disk ulamasangiz, har deploy'da ma'lumot o'chib ketishini unutmang (yuqoridagi "C" bandiga qarang).
- Render bepul tarifida xizmat uzoq vaqt faolsiz qolsa "uxlab" qolishi mumkin (bu odatda Web Service'larga tegishli, Background Worker'da kamroq uchraydi, lekin baribir vaqti-vaqti bilan Logs bo'limini tekshirib turing).
- Hozir har oy yangi hisob avtomatik boshlanadi (oy bo'yicha ажratilgan), lekin xodimning belgilangan oyligi har oy bir xil bo'lib qoladi — o'zgartirish kerak bo'lsa, kodga "oylikni yangilash" funksiyasini qo'shish mumkin (`database.py`da `update_employee_salary` funksiyasi tayyor turibdi, shunchaki botga tugma qo'shilmagan).

## Keyingi qadamlar (xohlasangiz qo'shib beraman)

- Excel/PDF hisobot eksport qilish
- Xodim oyligini o'zgartirish tugmasi
- Eski oylar bo'yicha statistika ko'rish (faqat joriy oy emas)
- Avtomatik USD/UZS kursini internetdan olib, qo'lda kiritmasdan hisoblash
