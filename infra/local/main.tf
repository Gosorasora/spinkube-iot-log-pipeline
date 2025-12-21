# k3d 로컬 개발 환경 설정
# KEDA, Prometheus를 설치합니다.
#
# 사전 요구사항:
#   k3d cluster create spinkube \
#     --image ghcr.io/spinkube/containerd-shim-spin/k3d:v0.17.0 \
#     -p "8081:80@loadbalancer" \
#     --agents 2
#
# 사용법:
#   cd infra/local
#   terraform init
#   terraform apply

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

  set {
    name  = "alertmanager.enabled"
    value = "false"
  }
}

# ============================================
# Outputs
# ============================================
output "grafana_access" {
  description = "Grafana 접속 정보"
  value = {
    url      = "kubectl port-forward svc/prometheus-grafana -n monitoring 3000:80"
    username = "admin"
    password = "admin123"
  }
}

output "next_steps" {
  description = "다음 단계 안내"
  value       = <<-EOT
    
    ✅ 인프라 설정 완료!
    
    Spin Operator 설치:
    1. kubectl apply -f https://github.com/spinframework/spin-operator/releases/download/v0.6.1/spin-operator.crds.yaml
    2. kubectl apply -f https://github.com/spinframework/spin-operator/releases/download/v0.6.1/spin-operator.runtime-class.yaml
    3. kubectl apply -f https://github.com/spinframework/spin-operator/releases/download/v0.6.1/spin-operator.shim-executor.yaml
    4. helm install spin-operator oci://ghcr.io/spinframework/charts/spin-operator --namespace spin-operator --create-namespace
    
    앱 배포:
    kubectl apply -f ../../k8s/spin-app.yaml
    
  EOT
}
