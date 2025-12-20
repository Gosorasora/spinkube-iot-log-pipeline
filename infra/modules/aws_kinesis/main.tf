# AWS Kinesis 모듈
# IoT 로그 수집을 위한 Kinesis Data Stream 및 관련 IAM 리소스

# Kinesis Data Stream
resource "aws_kinesis_stream" "iot_logs" {
  name             = var.stream_name
  shard_count      = var.shard_count
  retention_period = var.retention_period

  shard_level_metrics = [
    "IncomingBytes",
    "IncomingRecords",
    "OutgoingBytes",
    "OutgoingRecords",
    "WriteProvisionedThroughputExceeded",
    "ReadProvisionedThroughputExceeded",
    "IteratorAgeMilliseconds"
  ]

  stream_mode_details {
    stream_mode = "PROVISIONED"
  }

  tags = merge(var.tags, {
    Name        = var.stream_name
    Environment = var.environment
    Project     = "spinkube-iot"
  })
}

# KEDA가 Kinesis를 읽기 위한 IAM 정책
resource "aws_iam_policy" "keda_kinesis_policy" {
  name        = "keda-kinesis-${var.stream_name}-policy"
  description = "KEDA가 Kinesis 스트림을 모니터링하기 위한 정책"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kinesis:DescribeStream",
          "kinesis:DescribeStreamSummary",
          "kinesis:GetShardIterator",
          "kinesis:GetRecords",
          "kinesis:ListShards"
        ]
        Resource = aws_kinesis_stream.iot_logs.arn
      },
      {
        Effect = "Allow"
        Action = [
          "kinesis:ListStreams"
        ]
        Resource = "*"
      }
    ]
  })
}

# Spin 앱이 Kinesis에서 데이터를 읽기 위한 IAM 역할
resource "aws_iam_role" "spin_app_role" {
  name = "spin-app-kinesis-${var.stream_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${var.oidc_provider}"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${var.oidc_provider}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = var.tags
}

variable "oidc_provider" {
  description = "EKS OIDC Provider URL (eks.amazonaws.com/...)"
  type        = string
  default     = ""
}

data "aws_caller_identity" "current" {}

resource "aws_iam_role_policy_attachment" "spin_app_kinesis" {
  role       = aws_iam_role.spin_app_role.name
  policy_arn = aws_iam_policy.keda_kinesis_policy.arn
}

# CloudWatch 알람 (선택적)
resource "aws_cloudwatch_metric_alarm" "iterator_age" {
  alarm_name          = "${var.stream_name}-iterator-age-alarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "GetRecords.IteratorAgeMilliseconds"
  namespace           = "AWS/Kinesis"
  period              = 60
  statistic           = "Maximum"
  threshold           = 60000 # 1분 이상 지연 시 알람
  alarm_description   = "Kinesis 스트림 처리 지연 감지"

  dimensions = {
    StreamName = aws_kinesis_stream.iot_logs.name
  }

  tags = var.tags
}
