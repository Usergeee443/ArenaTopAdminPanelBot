#!/bin/bash
set -euo pipefail

APP_DIR="/opt/ArenaTopAdminPanelBot"
REPO="https://github.com/Usergeee443/ArenaTopAdminPanelBot.git"
SERVICE_NAME="arenatop-bot"

echo "==> ArenaTop bot o'rnatilmoqda: $APP_DIR"

if [ ! -f "$APP_DIR/main.py" ]; then
  echo "Xato: $APP_DIR/main.py topilmadi."
  echo "Avval to'g'ri klon qiling:"
  echo "  sudo rm -rf $APP_DIR"
  echo "  sudo git clone $REPO $APP_DIR"
  exit 1
fi

cd "$APP_DIR"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

mkdir -p data

if [ ! -f ".env" ]; then
  echo ""
  echo "DIQQAT: .env fayli yo'q!"
  echo "  cp .env.example .env"
  echo "  nano .env"
  echo "Keyin qayta ishga tushiring: systemctl restart $SERVICE_NAME"
  echo ""
fi

cp deploy/arenatop-bot.service /etc/systemd/system/${SERVICE_NAME}.service
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo ""
echo "Bot ishga tushirildi!"
echo "Holat:  systemctl status $SERVICE_NAME"
echo "Loglar: journalctl -u $SERVICE_NAME -f"
