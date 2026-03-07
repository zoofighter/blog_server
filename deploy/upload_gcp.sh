#!/bin/bash
# 로컬에서 Google Cloud 서버로 프로젝트 업로드
# 사용법: bash deploy/upload_gcp.sh <인스턴스명> [영역]
# 예시:   bash deploy/upload_gcp.sh blog-aggregator us-central1-a

set -e

INSTANCE="${1:?인스턴스명을 입력하세요: bash deploy/upload_gcp.sh <인스턴스명> [영역]}"
ZONE="${2:-us-central1-a}"
APP_DIR="/opt/blog-aggregator"
TMP_FILE="/tmp/blog-aggregator.tar.gz"

echo "=== GCP 서버로 프로젝트 업로드: $INSTANCE ($ZONE) ==="

# 1. 프로젝트를 tar로 압축 (불필요한 파일 제외)
echo "--- 압축 중..."
tar czf "$TMP_FILE" \
    --exclude='venv' \
    --exclude='data/blog.db' \
    --exclude='__pycache__' \
    --exclude='.DS_Store' \
    --exclude='*.pyc' \
    -C "$(pwd)" .

# 2. 서버로 전송
echo "--- 전송 중..."
gcloud compute scp "$TMP_FILE" "$INSTANCE:/tmp/" --zone="$ZONE"

# 3. 서버에서 압축 해제
echo "--- 서버에서 압축 해제 중..."
gcloud compute ssh "$INSTANCE" --zone="$ZONE" --command="
    sudo mkdir -p $APP_DIR
    sudo chown \$(whoami):\$(whoami) $APP_DIR
    tar xzf /tmp/blog-aggregator.tar.gz -C $APP_DIR/
    rm /tmp/blog-aggregator.tar.gz
"

# 로컬 임시 파일 삭제
rm -f "$TMP_FILE"

echo ""
echo "=== 업로드 완료 ==="
echo ""
echo "첫 배포 시 서버에서 실행:"
echo "  gcloud compute ssh $INSTANCE --zone=$ZONE"
echo "  sudo bash $APP_DIR/deploy/setup.sh"
echo ""
echo "코드 업데이트 시:"
echo "  gcloud compute ssh $INSTANCE --zone=$ZONE --command='sudo systemctl restart blog-aggregator'"
