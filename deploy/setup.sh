#!/bin/bash
# Oracle Cloud 서버 초기 셋업 스크립트
# 사용법: sudo bash setup.sh
set -e

APP_DIR="/opt/blog-aggregator"
APP_USER="ubuntu"

echo "=== 1. 시스템 패키지 업데이트 ==="
apt update && apt upgrade -y

echo "=== 2. Python 3.11 설치 ==="
apt install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt update
apt install -y python3.11 python3.11-venv python3.11-dev

echo "=== 3. Nginx 설치 ==="
apt install -y nginx

echo "=== 4. 프로젝트 디렉토리 설정 ==="
mkdir -p $APP_DIR
chown $APP_USER:$APP_USER $APP_DIR

echo "=== 5. Python 가상환경 생성 및 의존성 설치 ==="
sudo -u $APP_USER python3.11 -m venv $APP_DIR/venv
sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip
sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r $APP_DIR/requirements.txt

echo "=== 6. Nginx 설정 ==="
cp $APP_DIR/deploy/nginx.conf /etc/nginx/sites-available/blog-aggregator
ln -sf /etc/nginx/sites-available/blog-aggregator /etc/nginx/sites-enabled/blog-aggregator
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
systemctl enable nginx

echo "=== 7. systemd 서비스 등록 ==="
cp $APP_DIR/deploy/blog-aggregator.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable blog-aggregator
systemctl start blog-aggregator

echo "=== 8. iptables 방화벽 설정 (포트 80 오픈) ==="
iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
netfilter-persistent save 2>/dev/null || iptables-save > /etc/iptables/rules.v4 2>/dev/null || true

echo ""
echo "=== 셋업 완료 ==="
echo "서비스 상태: systemctl status blog-aggregator"
echo "로그 확인:   journalctl -u blog-aggregator -f"
echo ""
echo "중요: /etc/systemd/system/blog-aggregator.service 에서 비밀번호를 변경하세요:"
echo "  ADMIN_PASSWORD=your-password"
echo "  SECRET_KEY=your-random-string"
echo "변경 후: sudo systemctl daemon-reload && sudo systemctl restart blog-aggregator"
