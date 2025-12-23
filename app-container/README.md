# Container 버전 로그 분석 애플리케이션

SpinKube 버전과 동일한 로직을 Flask로 구현한 컨테이너 기반 애플리케이션입니다.

## 빌드 및 실행

### 로컬 테스트 (Python)

```bash
cd app-container

# 가상환경 생성
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 실행
python app.py
```

### Docker 빌드 및 실행

```bash
# 이미지 빌드
docker build -t log-analyzer-container:latest .

# 컨테이너 실행
docker run -d -p 3000:80 --name log-analyzer log-analyzer-container:latest

# 로그 확인
docker logs -f log-analyzer
```

### 테스트

```bash
# 헬스 체크
curl http://localhost:3000/health

# 정상 로그
curl -X POST http://localhost:3000/analyze \
  -H "Content-Type: application/json" \
  -d '{"device_id":"sensor-001","level":"INFO","response_time":100,"temperature":25}'

# 알림 발생 로그
curl -X POST http://localhost:3000/analyze \
  -H "Content-Type: application/json" \
  -d '{"device_id":"sensor-001","level":"ERROR","response_time":2500,"temperature":85,"message":"Connection failed"}'
```

### 성능 벤치마크

```bash
# 벤치마크 실행
cd ..
python3 simulation/benchmark.py --target http://localhost:3000/analyze --requests 1000 --concurrency 50
```

## Kubernetes 배포

```bash
# 이미지 푸시 (Azure Container Registry)
docker tag log-analyzer-container:latest <your-acr>.azurecr.io/log-analyzer-container:latest
docker push <your-acr>.azurecr.io/log-analyzer-container:latest

# Kubernetes 배포
kubectl apply -f ../k8s/container-app.yaml
```

## 성능 특성

### 예상 성능 (로컬 Docker)
- **콜드 스타트**: 3-5초
- **평균 응답 시간**: 50-100ms
- **메모리 사용량**: 200-300MB
- **이미지 크기**: ~150MB

### SpinKube 대비
- 콜드 스타트: 150-250배 느림
- 메모리: 3-5배 많음
- 이미지 크기: 10배 큼
