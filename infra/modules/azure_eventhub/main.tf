# Azure Event Hubs 모듈
# IoT 로그 수집을 위한 Event Hub (AWS Kinesis 대체)

variable "resource_group_name" {
  description = "리소스 그룹 이름"
  type        = string
}

variable "location" {
  description = "Azure 리전"
  type        = string
}

variable "namespace_name" {
  description = "Event Hub 네임스페이스 이름"
  type        = string
}

variable "eventhub_name" {
  description = "Event Hub 이름"
  type        = string
  default     = "iot-log-stream"
}

variable "partition_count" {
  description = "파티션 수 (처리량 결정)"
  type        = number
  default     = 4
}

variable "message_retention" {
  description = "메시지 보관 기간 (일)"
  type        = number
  default     = 1
}

variable "tags" {
  description = "리소스 태그"
  type        = map(string)
  default     = {}
}

# Event Hub Namespace
resource "azurerm_eventhub_namespace" "main" {
  name                = var.namespace_name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "Standard"
  capacity            = 1

  tags = var.tags
}

# Event Hub
resource "azurerm_eventhub" "main" {
  name                = var.eventhub_name
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = var.resource_group_name
  partition_count     = var.partition_count
  message_retention   = var.message_retention
}

# Consumer Group for KEDA
resource "azurerm_eventhub_consumer_group" "keda" {
  name                = "keda-consumer"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.main.name
  resource_group_name = var.resource_group_name
}

# Consumer Group for Spin App
resource "azurerm_eventhub_consumer_group" "spinapp" {
  name                = "spinapp-consumer"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.main.name
  resource_group_name = var.resource_group_name
}

# 인증 규칙 - KEDA (Listen)
resource "azurerm_eventhub_authorization_rule" "keda" {
  name                = "keda-auth"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.main.name
  resource_group_name = var.resource_group_name
  listen              = true
  send                = false
  manage              = false
}

# 인증 규칙 - Producer (Send)
resource "azurerm_eventhub_authorization_rule" "producer" {
  name                = "producer-auth"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.main.name
  resource_group_name = var.resource_group_name
  listen              = false
  send                = true
  manage              = false
}

# 인증 규칙 - Spin App (Listen)
resource "azurerm_eventhub_authorization_rule" "spinapp" {
  name                = "spinapp-auth"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.main.name
  resource_group_name = var.resource_group_name
  listen              = true
  send                = false
  manage              = false
}

output "namespace_name" {
  description = "Event Hub 네임스페이스 이름"
  value       = azurerm_eventhub_namespace.main.name
}

output "eventhub_name" {
  description = "Event Hub 이름"
  value       = azurerm_eventhub.main.name
}

output "keda_connection_string" {
  description = "KEDA용 연결 문자열"
  value       = azurerm_eventhub_authorization_rule.keda.primary_connection_string
  sensitive   = true
}

output "producer_connection_string" {
  description = "Producer용 연결 문자열"
  value       = azurerm_eventhub_authorization_rule.producer.primary_connection_string
  sensitive   = true
}

output "spinapp_connection_string" {
  description = "Spin App용 연결 문자열"
  value       = azurerm_eventhub_authorization_rule.spinapp.primary_connection_string
  sensitive   = true
}
