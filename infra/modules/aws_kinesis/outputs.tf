# AWS Kinesis 모듈 출력값

output "stream_name" {
  description = "Kinesis 스트림 이름"
  value       = aws_kinesis_stream.iot_logs.name
}

output "stream_arn" {
  description = "Kinesis 스트림 ARN"
  value       = aws_kinesis_stream.iot_logs.arn
}

output "keda_policy_arn" {
  description = "KEDA용 IAM 정책 ARN"
  value       = aws_iam_policy.keda_kinesis_policy.arn
}

output "spin_app_role_arn" {
  description = "Spin 앱용 IAM 역할 ARN"
  value       = aws_iam_role.spin_app_role.arn
}
