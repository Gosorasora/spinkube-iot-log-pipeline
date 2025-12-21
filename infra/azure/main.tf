# Azure AKS + SpinKube + Event Hubs 인프라
#
# 사용법:
#   az login
#   cd infra/azure
#   terraform init
#   terraform apply

locals {
  resource_prefix = "${var.project_name}-${var.environment}"
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# ============================================
# 1. Resource Group
# ============================================
resource "azurerm_resource_group" "main" {
  name     = "${local.resource_prefix}-rg"
  location = var.location
  tags     = local.common_tags
}

# ============================================
# 2. Virtual Network
# ============================================
resource "azurerm_virtual_network" "main" {
  name                = "${local.resource_prefix}-vnet"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = ["10.0.0.0/16"]
  tags                = local.common_tags
}

resource "azurerm_subnet" "aks" {
  name                 = "aks-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]
}

# ============================================
# 3. Azure Kubernetes Service (AKS)
# ============================================
resource "azurerm_kubernetes_cluster" "main" {
  name                = "${local.resource_prefix}-aks"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = local.resource_prefix
  kubernetes_version  = "1.29"

  default_node_pool {
    name                = "system"
    node_count          = 2
    vm_size             = "Standard_DS2_v2"
    vnet_subnet_id      = azurerm_subnet.aks.id
    os_disk_size_gb     = 30
    
    # 시스템 노드 풀 설정
    only_critical_addons_enabled = true
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin    = "azure"
    network_policy    = "calico"
    load_balancer_sku = "standard"
  }

  tags = local.common_tags
}

# ============================================
# 4. WASM 노드 풀 (SpinKube용)
# ============================================
# 참고: Azure WASI 노드 풀은 2025년 5월 deprecated
# SpinKube를 일반 노드 풀에 설치하는 방식 사용
resource "azurerm_kubernetes_cluster_node_pool" "wasm" {
  name                  = "wasmpool"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = "Standard_DS2_v2"
  node_count            = 2
  
  # WASM 워크로드용 레이블
  node_labels = {
    "workload-type" = "wasm"
  }

  node_taints = [
    "workload-type=wasm:NoSchedule"
  ]

  tags = local.common_tags
}

# ============================================
# 5. Azure Event Hubs (Kinesis 대체)
# ============================================
resource "azurerm_eventhub_namespace" "main" {
  name                = "${local.resource_prefix}-ehns"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Standard"
  capacity            = 1

  tags = local.common_tags
}

resource "azurerm_eventhub" "iot_logs" {
  name                = "iot-log-stream"
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = azurerm_resource_group.main.name
  partition_count     = 4
  message_retention   = 1  # 1일 보관
}

# Consumer Group for KEDA
resource "azurerm_eventhub_consumer_group" "keda" {
  name                = "keda-consumer"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.iot_logs.name
  resource_group_name = azurerm_resource_group.main.name
}

# Event Hub 인증 규칙
resource "azurerm_eventhub_authorization_rule" "keda" {
  name                = "keda-auth"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.iot_logs.name
  resource_group_name = azurerm_resource_group.main.name
  listen              = true
  send                = false
  manage              = false
}

resource "azurerm_eventhub_authorization_rule" "producer" {
  name                = "producer-auth"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.iot_logs.name
  resource_group_name = azurerm_resource_group.main.name
  listen              = false
  send                = true
  manage              = false
}

# ============================================
# 6. Azure Container Registry (ACR)
# ============================================
resource "azurerm_container_registry" "main" {
  name                = replace("${local.resource_prefix}acr", "-", "")
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = true

  tags = local.common_tags
}

# ACR과 AKS 연결
resource "azurerm_role_assignment" "aks_acr" {
  principal_id                     = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.main.id
  skip_service_principal_aad_check = true
}

# ============================================
# 7. Log Analytics (모니터링)
# ============================================
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${local.resource_prefix}-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = local.common_tags
}

# ============================================
# Outputs
# ============================================
output "resource_group_name" {
  description = "리소스 그룹 이름"
  value       = azurerm_resource_group.main.name
}

output "aks_cluster_name" {
  description = "AKS 클러스터 이름"
  value       = azurerm_kubernetes_cluster.main.name
}

output "aks_get_credentials" {
  description = "AKS 자격 증명 가져오기 명령어"
  value       = "az aks get-credentials --resource-group ${azurerm_resource_group.main.name} --name ${azurerm_kubernetes_cluster.main.name}"
}

output "acr_login_server" {
  description = "ACR 로그인 서버"
  value       = azurerm_container_registry.main.login_server
}

output "eventhub_namespace" {
  description = "Event Hub 네임스페이스"
  value       = azurerm_eventhub_namespace.main.name
}

output "eventhub_name" {
  description = "Event Hub 이름"
  value       = azurerm_eventhub.iot_logs.name
}

output "eventhub_connection_string" {
  description = "Event Hub 연결 문자열 (KEDA용)"
  value       = azurerm_eventhub_authorization_rule.keda.primary_connection_string
  sensitive   = true
}

output "next_steps" {
  description = "다음 단계"
  value       = <<-EOT
    
    ✅ Azure 인프라 생성 완료!
    
    다음 단계:
    1. AKS 자격 증명 가져오기:
       ${azurerm_kubernetes_cluster.main.name}
    
    2. SpinKube 설치:
       kubectl apply -f https://github.com/spinframework/spin-operator/releases/download/v0.6.1/spin-operator.crds.yaml
       helm install spin-operator oci://ghcr.io/spinframework/charts/spin-operator --namespace spin-operator --create-namespace
    
    3. KEDA 설치:
       helm install keda kedacore/keda --namespace keda --create-namespace
    
    4. Wasm 앱 배포:
       kubectl apply -f ../../k8s/spin-app.yaml
    
  EOT
}
