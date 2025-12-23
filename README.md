# SpinKube IoT Log Analyzer

WebAssembly(SpinKube)와 KEDA를 활용한 이벤트 기반 초고속 IoT 로그 처리 시스템

## 🎯 프로젝트 개요

대용량 IoT 센서 로그를 실시간으로 분석하고, 이상 징후 발생 시 자동으로 스케일링하는 시스템입니다.

### 핵심 기술 스택
- **Runtime**: SpinKube (WebAssembly on Kubernetes)
- **Language**: Python (componentize-py)
- **Autoscaling**: KEDA (Kubernetes Event-driven Autoscaling)
- **Monitoring**: Prometheus + Grafana
- **Infrastructure**: Terraform, k3d (로컬), Azure AKS (운영)
- **Message Queue**: Azure Event Hubs (운영 환경)

## 📁 프로젝트 구조

```
Spinkube/
├── app/                    # Wasm 애플리케이션 (Python)
│   ├── app.py              # 로그 분석 로직
│   ├── spin.toml           # Spin 설정
│   └── requirements.txt    # Python 의존성
├── infra/                  # Terraform IaC
│   ├── local/              # k3d 환경
│   └── azure/              # Azure AKS 환경
├── k8s/                    # Kubernetes 매니페스트
│   ├── spin-app.yaml       # SpinApp CRD
│   └── keda-scaler.yaml    # KEDA ScaledObject
└── simulation/             # 부하 테스트
    └── producer.py         # 로그 생성기
```

## 🚀 빠른 시작

### 1. 사전 요구사항

```bash
# k3d, kubectl, helm 설치
brew install k3d kubectl helm

# Spin CLI 설치
curl -fsSL https://developer.fermyon.com/downloads/install.sh | bash
sudo mv spin /usr/local/bin/

# Python 의존성
pip3 install requests aiohttp
```

### 2. k3d 클러스터 생성 (SpinKube 런타임 포함)

```bash
k3d cluster create spinkube \
  --image ghcr.io/spinkube/containerd-shim-spin/k3d:v0.17.0 \
  -p "8081:80@loadbalancer" \
  --agents 2
```

### 3. SpinKube 컴포넌트 설치

```bash
# Cert-Manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.4/cert-manager.yaml
kubectl wait --for=condition=available --timeout=120s deployment/cert-manager-webhook -n cert-manager

# Spin Operator
kubectl apply -f https://github.com/spinframework/spin-operator/releases/download/v0.6.1/spin-operator.crds.yaml
kubectl apply -f https://github.com/spinframework/spin-operator/releases/download/v0.6.1/spin-operator.runtime-class.yaml
kubectl apply -f https://github.com/spinframework/spin-operator/releases/download/v0.6.1/spin-operator.shim-executor.yaml
helm install spin-operator oci://ghcr.io/spinframework/charts/spin-operator --namespace spin-operator --create-namespace

# KEDA
helm install keda kedacore/keda --namespace keda --create-namespace

# Prometheus + Grafana
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --set grafana.adminPassword=admin123
```

### 4. Wasm 앱 빌드 및 배포

```bash
cd app
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
spin build
spin registry push ttl.sh/my-log-analyzer:1h

# K8s 배포
kubectl apply -f ../k8s/spin-app.yaml
```

### 5. 테스트

```bash
# 포트 포워딩
kubectl port-forward svc/log-analyzer-svc 3000:80

# 요청 테스트
curl -X POST http://localhost:3000/analyze \
  -H "Content-Type: application/json" \
  -d '{"level":"ERROR","response_time":2500,"device_id":"sensor-001","temperature":85}'
```

## 📊 모니터링

```bash
# Grafana 접속
kubectl port-forward svc/prometheus-grafana -n monitoring 3001:80
# http://localhost:3001 (admin / admin123)
```

## 🔧 로그 분석 임계값

| 항목 | 임계값 | 설명 |
|------|--------|------|
| ResponseTime | 2000ms | 응답 시간 초과 시 알림 |
| Temperature | 80°C | 온도 초과 시 알림 |
| Level | ERROR | ERROR 레벨 로그 감지 |

## 📈 성능 비교 (실측)

| 메트릭 | Docker Container | SpinKube (Wasm) | 개선율 |
|--------|------------------|-----------------|--------|
| Cold Start | 3-10초 | **15.76ms** | **99.8%** |
| 평균 응답 | 50-200ms | **11.79ms** | **76-94%** |
| 메모리 사용량 | 300-500MB | **59-98MB** | **70-93%** |
| 이미지 크기 | 100-500MB | **~15MB** | **97%** |
| 처리량 (2 pods) | ~200 req/s | **1,808 req/s** | **9배** |

### 성능 테스트

```bash
# 벤치마크 실행
python3 simulation/benchmark.py --requests 1000 --concurrency 20

# 리소스 모니터링 포함
python3 simulation/monitor_test.py
```

## 🧹 정리

```bash
k3d cluster delete spinkube
```
