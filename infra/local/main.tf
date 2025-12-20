# 로컬 개발 환경 (Minikube) 설정
# KEDA, Prometheus, Cert-Manager, Spin-Operator를 설치합니다.
#
# 사용법:
#   1. minikube start --memory=4096 --cpus=2
#   2. cd infra/local
#   3. terraform init
#   4. terraform apply

locals {
  namespace = "spinkube-system"
}

# SpinKube 시스템 네임스페이스
resource "kubernetes_namespace" "spinkube" {
  metadata {
    name = local.namespace
    labels = {
      "app.kubernetes.io/managed-by" = "terraform"
      "project"                      = "spinkube-iot"
    }
  }
}

# ============================================
# 1. Cert-Manager (Spin Operator 의존성)
# ============================================
resource "helm_release" "cert_manager" {
  name             = "cert-manager"
  repository       = "https://charts.jetstack.io"
  chart            = "cert-manager"
  version          = "v1.14.4"
  namespace        = "cert-manager"
  create_namespace = true

  set {
    name  = "installCRDs"
    value = "true"
  }

  # 로컬 환경 리소스 최적화
  set {
    name  = "resources.requests.cpu"
    value = "50m"
  }

  set {
    name  = "resources.requests.memory"
    value = "64Mi"
  }
}

# ============================================
# 2. KEDA - 이벤트 기반 오토스케일링
# ============================================
resource "helm_release" "keda" {
  name             = "keda"
  repository       = "https://kedacore.github.io/charts"
  chart            = "keda"
  version          = "2.13.1"
  namespace        = "keda"
  create_namespace = true

  # 로컬 환경 최적화
  set {
    name  = "resources.operator.requests.cpu"
    value = "50m"
  }

  set {
    name  = "resources.operator.requests.memory"
    value = "64Mi"
  }

  set {
    name  = "resources.metricServer.requests.cpu"
    value = "50m"
  }

  set {
    name  = "resources.metricServer.requests.memory"
    value = "64Mi"
  }
}

# ============================================
# 3. Prometheus + Grafana 모니터링 스택
# ============================================
resource "helm_release" "prometheus_stack" {
  name             = "prometheus"
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  version          = "57.1.1"
  namespace        = "monitoring"
  create_namespace = true

  # Grafana 설정
  set {
    name  = "grafana.adminPassword"
    value = "admin123"
  }

  set {
    name  = "grafana.service.type"
    value = "NodePort"
  }

  set {
    name  = "grafana.service.nodePort"
    value = "30080"
  }

  # 로컬 환경 리소스 최적화
  set {
    name  = "prometheus.prometheusSpec.resources.requests.memory"
    value = "256Mi"
  }

  set {
    name  = "prometheus.prometheusSpec.resources.requests.cpu"
    value = "100m"
  }

  set {
    name  = "prometheus.prometheusSpec.retention"
    value = "6h"
  }

  # AlertManager 비활성화 (로컬에서는 불필요)
  set {
    name  = "alertmanager.enabled"
    value = "false"
  }
}

# ============================================
# 4. Spin Operator CRDs
# ============================================
resource "helm_release" "spin_operator_crds" {
  name      = "spin-operator-crds"
  chart     = "oci://ghcr.io/spinkube/charts/spin-operator-crds"
  version   = "0.2.0"
  namespace = local.namespace

  depends_on = [kubernetes_namespace.spinkube]
}

# ============================================
# 5. Spin Operator
# ============================================
resource "helm_release" "spin_operator" {
  name      = "spin-operator"
  chart     = "oci://ghcr.io/spinkube/charts/spin-operator"
  version   = "0.2.0"
  namespace = local.namespace

  depends_on = [
    kubernetes_namespace.spinkube,
    helm_release.cert_manager,
    helm_release.spin_operator_crds
  ]
}

# ============================================
# 6. RuntimeClass for Spin (wasmtime-spin-v2)
# ============================================
resource "kubernetes_manifest" "spin_runtime_class" {
  manifest = {
    apiVersion = "node.k8s.io/v1"
    kind       = "RuntimeClass"
    metadata = {
      name = "wasmtime-spin-v2"
    }
    handler = "spin"
  }

  depends_on = [helm_release.spin_operator]
}

# ============================================
# Outputs
# ============================================
output "grafana_access" {
  description = "Grafana 접속 정보"
  value = {
    url      = "http://localhost:30080"
    username = "admin"
    password = "admin123"
  }
}

output "keda_namespace" {
  description = "KEDA 네임스페이스"
  value       = "keda"
}

output "spinkube_namespace" {
  description = "SpinKube 네임스페이스"
  value       = local.namespace
}

output "next_steps" {
  description = "다음 단계 안내"
  value       = <<-EOT
    
    ✅ 로컬 환경 설정 완료!
    
    다음 단계:
    1. kubectl get pods -A  # 모든 파드 상태 확인
    2. kubectl apply -f ../../k8s/spin-app.yaml  # Spin 앱 배포
    3. kubectl apply -f ../../k8s/keda-scaler.yaml  # KEDA 스케일러 설정
    4. minikube service grafana -n monitoring  # Grafana 접속
    
  EOT
}
