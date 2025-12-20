# K8s Addons 모듈
# KEDA, Prometheus, Grafana, Cert-Manager, Spin-Operator를 설치합니다.

variable "namespace" {
  description = "애드온을 설치할 네임스페이스"
  type        = string
  default     = "spinkube-system"
}

variable "enable_keda" {
  description = "KEDA 설치 여부"
  type        = bool
  default     = true
}

variable "enable_prometheus" {
  description = "Prometheus 스택 설치 여부"
  type        = bool
  default     = true
}

variable "enable_cert_manager" {
  description = "Cert-Manager 설치 여부"
  type        = bool
  default     = true
}

variable "enable_spin_operator" {
  description = "Spin Operator 설치 여부"
  type        = bool
  default     = true
}

# 네임스페이스 생성
resource "kubernetes_namespace" "spinkube" {
  metadata {
    name = var.namespace
  }
}

# Cert-Manager (Spin Operator의 의존성)
resource "helm_release" "cert_manager" {
  count = var.enable_cert_manager ? 1 : 0

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

  set {
    name  = "webhook.timeoutSeconds"
    value = "30"
  }
}

# KEDA - Kubernetes Event-driven Autoscaling
resource "helm_release" "keda" {
  count = var.enable_keda ? 1 : 0

  name             = "keda"
  repository       = "https://kedacore.github.io/charts"
  chart            = "keda"
  version          = "2.13.1"
  namespace        = "keda"
  create_namespace = true

  set {
    name  = "metricsServer.replicaCount"
    value = "1"
  }
}

# Prometheus + Grafana 스택
resource "helm_release" "prometheus_stack" {
  count = var.enable_prometheus ? 1 : 0

  name             = "prometheus"
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  version          = "57.1.1"
  namespace        = "monitoring"
  create_namespace = true

  # Grafana 기본 설정
  set {
    name  = "grafana.adminPassword"
    value = "admin123"
  }

  set {
    name  = "grafana.service.type"
    value = "NodePort"
  }

  # 리소스 제한 (로컬 환경용)
  set {
    name  = "prometheus.prometheusSpec.resources.requests.memory"
    value = "256Mi"
  }

  set {
    name  = "prometheus.prometheusSpec.resources.requests.cpu"
    value = "100m"
  }
}

# Spin Operator (SpinKube)
resource "helm_release" "spin_operator" {
  count = var.enable_spin_operator ? 1 : 0

  name             = "spin-operator"
  repository       = "oci://ghcr.io/spinkube/charts"
  chart            = "spin-operator"
  version          = "0.2.0"
  namespace        = var.namespace

  depends_on = [
    kubernetes_namespace.spinkube,
    helm_release.cert_manager
  ]
}

# Spin Operator CRDs (별도 설치 필요)
resource "helm_release" "spin_operator_crds" {
  count = var.enable_spin_operator ? 1 : 0

  name       = "spin-operator-crds"
  repository = "oci://ghcr.io/spinkube/charts"
  chart      = "spin-operator-crds"
  version    = "0.2.0"
  namespace  = var.namespace

  depends_on = [kubernetes_namespace.spinkube]
}

# RuntimeClass for Spin (wasmtime-spin-v2)
resource "kubernetes_manifest" "spin_runtime_class" {
  count = var.enable_spin_operator ? 1 : 0

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

output "grafana_url" {
  description = "Grafana 접속 URL (NodePort)"
  value       = var.enable_prometheus ? "http://localhost:30080" : null
}

output "namespace" {
  description = "SpinKube 네임스페이스"
  value       = var.namespace
}
