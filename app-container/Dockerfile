# Container 버전 로그 분석 애플리케이션
# Python Flask 기반

FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY app.py .

# 포트 노출
EXPOSE 80

# 헬스 체크
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:80/health')" || exit 1

# Gunicorn으로 실행 (프로덕션)
CMD ["gunicorn", "--bind", "0.0.0.0:80", "--workers", "4", "--threads", "2", "--timeout", "30", "app:app"]
