#!/bin/bash
# 로컬에서 Oracle Cloud 서버로 프로젝트 업로드
# 사용법: bash deploy/upload.sh <서버IP> <SSH키경로>
# 예시:   bash deploy/upload.sh 129.154.xx.xx ~/.ssh/oracle_key

set -e

SERVER_IP="${1:?서버 IP를 입력하세요: bash deploy/upload.sh <IP> <SSH키>}"
SSH_KEY="${2:?SSH 키 경로를 입력하세요: bash deploy/upload.sh <IP> <SSH키>}"
SSH_USER="ubuntu"
APP_DIR="/opt/blog-aggregator"

echo "=== 서버로 프로젝트 업로드: $SSH_USER@$SERVER_IP ==="

# rsync로 필요한 파일만 전송
rsync -avz --progress \
    -e "ssh -i $SSH_KEY" \
    --exclude='venv/' \
    --exclude='data/blog.db' \
    --exclude='__pycache__/' \
    --exclude='.DS_Store' \
    --exclude='*.pyc' \
    ./ $SSH_USER@$SERVER_IP:$APP_DIR/

echo ""
echo "=== 업로드 완료 ==="
echo ""
echo "첫 배포 시 서버에서 실행:"
echo "  ssh -i $SSH_KEY $SSH_USER@$SERVER_IP"
echo "  sudo bash $APP_DIR/deploy/setup.sh"
echo ""
echo "코드 업데이트 시 서버에서 실행:"
echo "  ssh -i $SSH_KEY $SSH_USER@$SERVER_IP 'sudo systemctl restart blog-aggregator'"
