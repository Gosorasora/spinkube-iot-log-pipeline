# K8s Addons 모듈 출력값

output "keda_installed" {
  description = "KEDA 설치 여부"
  value       = var.enable_keda
}

output "prometheus_installed" {
  description = "Prometheus 스택 설치 여부"
  value       = var.enable_prometheus
}

output "spin_operator_installed" {
  description = "Spin Operator 설치 여부"
  value       = var.enable_spin_operator
}
