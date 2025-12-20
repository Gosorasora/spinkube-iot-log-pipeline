# 로컬 개발 환경용 Provider 설정
# Minikube 클러스터를 대상으로 합니다.

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.27.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12.0"
    }
  }
}

# Kubernetes Provider - Minikube 연결
provider "kubernetes" {
  config_path    = var.kubeconfig_path
  config_context = var.kubeconfig_context
}

# Helm Provider - Minikube 연결
provider "helm" {
  kubernetes {
    config_path    = var.kubeconfig_path
    config_context = var.kubeconfig_context
  }
}

variable "kubeconfig_path" {
  description = "kubeconfig 파일 경로"
  type        = string
  default     = "~/.kube/config"
}

variable "kubeconfig_context" {
  description = "사용할 kubeconfig 컨텍스트 (minikube)"
  type        = string
  default     = "minikube"
}
