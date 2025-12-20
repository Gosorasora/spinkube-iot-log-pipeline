# AWS 운영 환경 설정 (EKS + Kinesis)
# 
# TODO: 로컬 테스트 완료 후 구현 예정
# 
# 포함 예정 리소스:
# - EKS 클러스터
# - Kinesis Data Stream
# - IAM 역할 (IRSA)
# - VPC 및 서브넷

locals {
  cluster_name = "spinkube-iot-cluster"
  region       = "ap-northeast-2"
  environment  = "dev"
}

# 추후 구현 예정
# module "eks" { ... }
# module "kinesis" { ... }
