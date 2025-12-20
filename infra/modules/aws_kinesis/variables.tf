# AWS Kinesis 모듈 변수 정의

variable "stream_name" {
  description = "Kinesis Data Stream 이름"
  type        = string
  default     = "iot-log-stream"
}

variable "shard_count" {
  description = "Kinesis 샤드 수"
  type        = number
  default     = 2
}

variable "retention_period" {
  description = "데이터 보존 기간 (시간)"
  type        = number
  default     = 24
}

variable "environment" {
  description = "환경 (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "tags" {
  description = "리소스 태그"
  type        = map(string)
  default     = {}
}
