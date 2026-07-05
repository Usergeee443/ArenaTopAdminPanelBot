# ArenaTop Admin Telegram Bot

ArenaTop platformasi uchun yordamchi Telegram bot. Adminlarga **pul qaytarish** va **pul yechish** so'rovlarini avtomatik yuboradi.

## Imkoniyatlar

### 💰 Pul so'rovlari (asosiy)
- Pul qaytarish so'rovlarini kuzatish va ko'rish
- Pul yechish so'rovlarini kuzatish va ko'rish
- Yangi so'rovlar kelganda avtomatik xabar
- Qo'lda tekshirish

### 📊 Statistika
- Dashboard (foydalanuvchilar, bronlar, to'lovlar)
- Foydalanuvchilar statistikasi
- Bugungi daromad

### 📋 Boshqa
- Bronlar ro'yxati (holat bo'yicha)
- Maydonlar ro'yxati
- Profil ma'lumotlari
- Tugmalar bilan qulay interfeys

## Interfeys

Bot **tugmalar** bilan ishlaydi:

```
💰 Pul so'rovlari | 📊 Statistika
📋 Bronlar        | 🏟 Maydonlar
👤 Profil         | ⚙️ Sozlamalar
```

Har bo'limda inline tugmalar (yangilash, orqaga) mavjud.

## O'rnatish

```bash
cd arenatopadminbot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` faylini to'ldiring:

| O'zgaruvchi | Tavsif |
|---|---|
| `TELEGRAM_BOT_TOKEN` | @BotFather dan olingan bot token |
| `ADMIN_TELEGRAM_IDS` | Admin Telegram ID lari (vergul bilan) |
| `ARENATOP_API_TOKEN` | ArenaTop API Bearer token (ixtiyoriy) |
| `ARENATOP_PHONE` | Admin telefon raqami (default: `917079732`) |
| `ARENATOP_API_BASE_URL` | API manzili (default: `https://api.arenatop.uz/v1`) |
| `POLL_INTERVAL_SECONDS` | Tekshirish intervali (default: 60) |

### Admin Telegram ID ni olish

1. [@userinfobot](https://t.me/userinfobot) ga `/start` yuboring
2. Qaytgan `Id` ni `ADMIN_TELEGRAM_IDS` ga qo'shing

## Ishga tushirish

```bash
python main.py
```

## Login (telefon orqali)

Bot ishga tushganda `ARENATOP_PHONE` raqamiga SMS kod yuboradi. Admin Telegram botga kodni yuboradi va token avtomatik saqlanadi.

| O'zgaruvchi | Tavsif |
|---|---|
| `ARENATOP_PHONE` | ArenaTop admin telefon raqami (masalan: `917079732`) |
| `ARENATOP_API_TOKEN` | Ixtiyoriy statik token (bo'lsa, SMS login o'tkazib yuboriladi) |

### Login jarayoni

1. Bot ishga tushadi
2. Saqlangan token yo'q bo'lsa, SMS kod yuboriladi
3. Admin kodni botga yuboradi (masalan: `123456`)
4. Token `data/auth_session.json` ga saqlanadi
5. Keyingi ishga tushirishlarda qayta login shart emas

Qayta login uchun: `/login`

## API endpointlar

Bot quyidagi ArenaTop API endpointlaridan foydalanadi:

- `GET /refund-requests` — pul qaytarish so'rovlari
- `GET /withdrawals?scope=platform` — pul yechish so'rovlari
- `GET /settings/dashboard` — dashboard statistikasi
- `GET /users/summary` — foydalanuvchilar
- `GET /users/me/statistics` — bugungi daromad
- `GET /bookings?scope=platform` — bronlar
- `GET /courts?scope=all` — maydonlar

Autentifikatsiya: telefon orqali OTP login (avtomatik)

## Buyruqlar

| Buyruq | Vazifa |
|---|---|
| `/start` yoki `/menu` | Asosiy menyu (tugmalar) |
| `/pending` | Pul so'rovlari |
| `/check` | Yangi so'rovlarni tekshirish |
| `/login` | Qayta login |
| `/help` | Yordam |

## Eslatma

Bot birinchi marta ishga tushganda mavjud so'rovlarni "ko'rilgan" deb belgilaydi — shunda eski so'rovlar qayta yuborilmaydi. Keyin faqat **yangi** so'rovlar haqida xabar beriladi.
