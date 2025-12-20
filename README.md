# SpinKube IoT Log Analyzer

WebAssembly(SpinKube)와 KEDA를 활용한 이벤트 기반 초고속 IoT 로그 처리 시스템

## 🎯 프로젝트 개요

대용량 IoT 센서 로그를 실시간으로 분석하고, 이상 징후 발생 시 자동으로 스케일링하는 시스템입니다.

### 핵심 기술 스택
- **Runtime**: SpinKube (WebAssembly on Kubernetes)
- **Language**: Go (TinyGo 컴파일러)
- **Autoscaling**: KEDA (Kubernetes Event-driven Autoscaling)
- **Monitoring**: Prometheus + Grafana
- **Infrastructure**: Terraform
- **Message Queue**: AWS Kinesis (운영 환경)

## 📁 프로젝트 구조

```
Spinkube/
├── app/                    # Wasm 애플리케이션 (Go)
│   ├── main.go             # 로그 분석 로직
│   ├── spin.toml           # Spin 설정
│   └── Dockerfile          # OCI 이미지 빌드
├── infra/                  # Terraform IaC
│   ├── local/              # Minikube 환경
│   └── aws/                # EKS 환경 (예정)
├── k8s/                    # Kubernetes 매니페스트
│   ├── spin-app.yaml       # SpinApp CRD
│   └── keda-scaler.yaml    # KEDA ScaledObject
└── simulation/             # 부하 테스트
    └── producer.py         # 로그 생성기
```

## 🚀 빠른 시작 (로컬 환경)

### 1. 사전 요구사항

```bash
# Minikube 설치
brew install minikube

# Terraform 설치
brew install terraform

# Spin CLI 설치
curl -fsSL https://developer.fermyon.com/downloads/install.sh | bash

# TinyGo 설치
brew install tinygo
```

### 2. Minikube 클러스터 시작

```bash
minikube start --memory=4096 --cpus=2
```

### 3. 인프라 배포 (KEDA, Prometheus, Spin Operator)

```bash
cd infra/local
terraform init
terraform apply
```

### 4. Wasm 애플리케이션 빌드

```bash
cd app
spin build
```

### 5. OCI 레지스트리에 푸시

```bash
# GitHub Container Registry 로그인
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Spin 앱 푸시
spin registry push ghcr.io/your-username/spinkube-log-analyzer:v1
```

### 6. SpinApp 배포

```bash
# spin-app.yaml의 image를 실제 레지스트리 주소로 수정 후
kubectl apply -f k8s/spin-app.yaml
kubectl apply -f k8s/keda-scaler.yaml
```

### 7. 부하 테스트

```bash
cd simulation
pip install -r requirements.txt

# 포트 포워딩
kubectl port-forward svc/log-analyzer-svc -n spinkube-system 8080:80

# 테스트 실행
python producer.py --mode http --rate 100 --duration 60
```

## 📊 모니터링

### Grafana 접속

```bash
# 포트 포워딩
kubectl port-forward svc/prometheus-grafana -n monitoring 3000:80

# 브라우저에서 http://localhost:3000 접속
# ID: admin / PW: admin123
```

## 🔧 주요 설정

### 로그 분석 임계값 (app/main.go)

| 항목 | 임계값 | 설명 |
|------|--------|------|
| ResponseTime | 2000ms | 응답 시간 초과 시 알림 |
| Temperature | 80°C | 온도 초과 시 알림 |
| Level | ERROR | ERROR 레벨 로그 감지 |

### KEDA 스케일링 설정 (k8s/keda-scaler.yaml)

| 항목 | 값 | 설명 |
|------|-----|------|
| minReplicaCount | 1 | 최소 파드 수 |
| maxReplicaCount | 10 | 최대 파드 수 |
| cooldownPeriod | 30s | 스케일 다운 대기 시간 |
| threshold | 100 req/s | 스케일 아웃 임계값 |

## 📈 성능 비교 (예상)

| 메트릭 | Docker Container | SpinKube (Wasm) |
|--------|------------------|-----------------|
| Cold Start | 3-5초 | < 50ms |
| 메모리 사용량 | 100-500MB | 10-50MB |
| 이미지 크기 | 100-500MB | 1-5MB |

## 🗓️ 개발 로드맵

- [x] Week 1-2: 로컬 환경 구축
- [ ] Week 3-5: Wasm 모듈 개발 및 테스트
- [ ] Week 6-7: AWS EKS + Kinesis 통합
- [ ] Week 8: 성능 측정 및 보고서 작성

## 📚 참고 자료

- [SpinKube Documentation](https://www.spinkube.dev/)
- [KEDA Documentation](https://keda.sh/)
- [Fermyon Spin](https://developer.fermyon.com/spin)
- [TinyGo](https://tinygo.org/)
