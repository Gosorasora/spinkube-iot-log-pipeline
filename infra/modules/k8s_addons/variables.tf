# K8s Addons 모듈 변수 정의

variable "kubeconfig_path" {
  description = "kubeconfig 파일 경로"
  type        = string
  default     = "~/.kube/config"
}

variable "kubeconfig_context" {
  description = "사용할 kubeconfig 컨텍스트"
  type        = string
  default     = "minikube"
}
