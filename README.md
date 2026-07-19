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
| `ADMIN_TELEGRAM_IDS` | Ixtiyoriy Telegram ID ro'yxati; bo'sh bo'lsa istalgan moderator OTP orqali kiradi |
| `ARENATOP_API_TOKEN` | ArenaTop API Bearer token (ixtiyoriy) |
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

Har bir moderator o'z telefon raqami bilan kiradi:

1. `/start` yoki `/login`
2. Telefon raqamini yuboradi (masalan: `917079732`)
3. SMS kelgan kodni yuboradi
4. Token shu Telegram foydalanuvchi uchun saqlanadi

| O'zgaruvchi | Tavsif |
|---|---|
| `ADMIN_TELEGRAM_IDS` | Ixtiyoriy ruxsatlar ro'yxati. Bo'sh bo'lsa — OTP orqali kirgan har qanday moderator ishlata oladi |
| `ARENATOP_API_TOKEN` | Ixtiyoriy statik token (bo'lsa, SMS login o'tkazib yuboriladi) |

Qayta login: `/login` yoki Sozlamalar → Qayta login

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

## Serverga o'rnatish (doimiy ishlashi uchun)

Bot **systemd** xizmati sifatida ishlaydi — server qayta yuklansa ham avtomatik ishga tushadi.

### 1. To'g'ri klon qiling

```bash
sudo rm -rf /opt/ArenaTopAdminPanelBot
sudo git clone https://github.com/Usergeee443/ArenaTopAdminPanelBot.git /opt/ArenaTopAdminPanelBot
cd /opt/ArenaTopAdminPanelBot
```

> **Muhim:** `git clone` ni to'g'ridan-to'g'ri `/opt/ArenaTopAdminPanelBot` ga qiling. Ichma-ich papka bo'lmasin.

### 2. `.env` sozlang

```bash
cp .env.example .env
nano .env
```

### 3. O'rnatish skripti

```bash
chmod +x deploy/install.sh
sudo ./deploy/install.sh
```

### 4. Foydali buyruqlar

```bash
# Holat
sudo systemctl status arenatop-bot

# Loglar (jonli)
sudo journalctl -u arenatop-bot -f

# Qayta ishga tushirish
sudo systemctl restart arenatop-bot

# To'xtatish
sudo systemctl stop arenatop-bot
```

### Kod yangilanganda

```bash
cd /opt/ArenaTopAdminPanelBot
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart arenatop-bot
```
