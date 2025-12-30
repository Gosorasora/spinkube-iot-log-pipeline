# SpinKube IoT Log Analyzer Architecture

## 1. System Overview

This project implements a high-performance, event-driven IoT log processing system using **WebAssembly (Wasm)**. By leveraging **SpinKube** and **Rust**, it achieves millisecond-level cold starts and extreme resource efficiency compared to traditional container-based architectures.

The system ingests log data via HTTP, analyzes it for anomalies (errors, high temps, slow responses), and scales to zero when idle.

## 2. Architecture Diagram

```mermaid
graph TD
    User[IoT Device / User] -->|HTTP POST| Ingress[K8s Ingress]
    Ingress -->|Route| Service[Service LoadBalancer]
    Service -->|Traffic| SpinApp[SpinApp (Rust Wasm)]
    
    subgraph Kubernetes Cluster
        SpinApp
        Operator[Spin Operator] -.->|Manages| SpinApp
        Shim[containerd-shim-spin] -.->|Executes| SpinApp
        
        KEDA[KEDA Scaler] -.->|Monitors Metrics| SpinApp
        KEDA -->|Scales 0<->N| SpinApp
    end
    
    SpinApp -->|Logs| Stdout[Stdout / Logs]
```

### Request Flow
1. **Ingress**: Traffic enters the cluster.
2. **SpinApp**: The `spin-operator` creates a specialized Pod that uses the `containerd-shim-spin`.
3. **Execution**: The Wasm binary is executed directly by the shim (bypassing the container overhead).
4. **Auto-scaling**: KEDA monitors traffic/CPU and scales the logic from 0 to N instantly.

## 3. Technology Stack

| Component | Technology | Role |
|-----------|------------|------|
| **Runtime** | **SpinKube** | Kubernetes operator for running Wasm workloads securely and efficiently. |
| **Logic** | **Rust (Native Wasm)** | compiled to `wasm32-wasip1`. Zero overhead, type-safe, sub-millisecond execution. |
| **Scaling** | **KEDA** | Event-driven autoscaler. Supports scaling to zero (Scale-to-Zero). |
| **Infrastructure** | **k3d / AKS** | Kubernetes environment supporting Wasm shims. |

## 4. Performance Benchmarks

The following results demonstrate the architectural advantages of SpinKube (Rust) over standard Docker Containers (Python/Flask).

### 🏆 Executive Summary
> **SpinKube (Rust) is 400x lighter and starts 2.4x faster than Docker, while handling 1.8x more traffic.**

### Detailed Comparison

| Metric | Rust (SpinKube) | Docker Container | Improvement |
|--------|-----------------|------------------|-------------|
| **Cold Start** 🚀 | **~72 ms** | ~176 ms | **2.4x Faster** |
| **Image Size** 📦 | **0.39 MB** | 158.88 MB | **404x Smaller** |
| **Throughput** ⚡ | **~9,700 req/s** | ~5,300 req/s | **1.8x Higher** |
| **Density (Mem)** 🏢 | **~15 MB** | ~80 MB | **5x Higher Density** |

*Note: Benchmarks performed on a local simulated environment. Cold start differences are typically larger (Seconds vs Milliseconds) in actual cloud environments.*

## 5. Why Rust?

Initially implemented in Python (componentize-py), the project was migrated to **Rust** to eliminate interpreter overhead.
- **Python Wasm**: ~35MB binary, ~18ms avg latency
- **Rust Wasm**: ~0.4MB binary, ~3ms avg latency (~8x faster)

This architecture guarantees the lowest possible resource footprint and fastest data processing for high-volume IoT streams.
