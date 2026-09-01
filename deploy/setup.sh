#!/usr/bin/env bash
# راه‌انداز سرور Hetzner برای داشبورد تحلیل جذب و استخدام — بدون دامنه، فقط با آی‌پی.
#
# پیش‌نیاز: کد پروژه از قبل در /opt/hr-dashboard روی سرور باشد (با rsync/scp/git).
# اجرا: به‌عنوان root روی سرور تازه (Ubuntu 22.04/24.04)
#
#   sudo bash deploy/setup.sh
#
# نکته امنیتی: بدون دامنه، SSL واقعی (Let's Encrypt) ممکن نیست چون به یک نام دامنه
# نیاز دارد نه آی‌پی. این یعنی ترافیک—از جمله رمز Basic Auth—رمزنگاری‌نشده روی شبکه
# رد می‌شود. برای یک ابزار داخلی/آزمایشی قابل قبول است؛ برای داده حساس روی اینترنت
# باز، بعداً یک دامنه بگیرید و از راهنمای نسخه SSL استفاده کنید.
set -euo pipefail

APP_DIR=/opt/hr-dashboard
APP_USER=hrapp

echo "==> نصب بسته‌های سیستمی"
apt-get update -qq
apt-get install -y python3-venv python3-pip nginx apache2-utils ufw

echo "==> ساخت کاربر بدون-پوسته برای اجرای برنامه (نه root)"
id -u "$APP_USER" &>/dev/null || useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"

echo "==> محیط مجازی پایتون و نصب وابستگی‌ها"
cd "$APP_DIR"
python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

echo "==> نصب سرویس systemd"
cp deploy/hr-dashboard.service /etc/systemd/system/hr-dashboard.service
systemctl daemon-reload
systemctl enable --now hr-dashboard

echo "==> رمز عبور Basic Auth (کاربر: hr)"
if [ ! -f /etc/nginx/.htpasswd ]; then
  if [ -n "${HR_PASSWORD:-}" ]; then
    # اجرای غیرتعاملی: رمز از متغیر محیطی HR_PASSWORD خوانده می‌شود
    htpasswd -cb /etc/nginx/.htpasswd hr "$HR_PASSWORD"
  else
    htpasswd -c /etc/nginx/.htpasswd hr
  fi
else
  echo "   /etc/nginx/.htpasswd از قبل هست — رد شد"
fi

echo "==> کانفیگ nginx"
cp deploy/nginx.conf /etc/nginx/sites-available/hr-dashboard
ln -sf /etc/nginx/sites-available/hr-dashboard /etc/nginx/sites-enabled/hr-dashboard
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "==> فایروال"
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

SERVER_IP=$(curl -s -4 https://icanhazip.com || hostname -I | awk '{print $1}')
echo
echo "تمام شد: http://${SERVER_IP}"
echo "بررسی وضعیت سرویس:  systemctl status hr-dashboard"
echo "لاگ زنده:            journalctl -u hr-dashboard -f"
