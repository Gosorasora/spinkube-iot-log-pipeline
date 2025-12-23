#!/usr/bin/env python3
"""
Container vs SpinKube 리소스 비교 테스트

동일한 부하에서 Container와 SpinKube의 리소스 사용량과 처리 속도를 비교합니다.

측정 항목:
  1. 파드 수
  2. CPU 사용량
  3. 메모리 사용량
  4. 처리량
  5. 응답 시간
  6. 스케일 아웃 시간

사용법:
  python resource_comparison.py --container-url http://localhost:8082/analyze --spinkube-url http://localhost:8081/analyze --requests 10000 --concurrency 500
"""

import argparse
import asyncio
import json
import subprocess
import statistics
import time
from datetime import datetime

try:
    import aiohttp
except ImportError:
    print("aiohttp 필요: pip install aiohttp")
    exit(1)


def run_kubectl(cmd):
    """kubectl 명령 실행"""
    result = subprocess.run(
        f"kubectl {cmd}",
        shell=True,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


def get_pod_metrics(label):
    """파드 메트릭 조회"""
    output = run_kubectl(f"top pods -l {label} --no-headers")
    if not output:
        return []
    
    metrics = []
    for line in output.split('\n'):
        if line.strip():
            parts = line.split()
            if len(parts) >= 3:
                metrics.append({
                    'name': parts[0],
                    'cpu': parts[1],
                    'memory': parts[2]
                })
    return metrics


def get_pod_count(label):
    """파드 수 조회"""
    output = run_kubectl(f"get pods -l {label} --no-headers")
    if not output:
        return 0
    return len([line for line in output.split('\n') if line.strip()])


def parse_cpu(cpu_str):
    """CPU 문자열을 밀리코어로 변환 (예: 100m -> 100, 1 -> 1000)"""
    if cpu_str.endswith('m'):
        return int(cpu_str[:-1])
    else:
        return int(cpu_str) * 1000


def parse_memory(mem_str):
    """메모리 문자열을 MB로 변환 (예: 100Mi -> 100, 1Gi -> 1024)"""
    if mem_str.endswith('Mi'):
        return int(mem_str[:-2])
    elif mem_str.endswith('Gi'):
        return int(mem_str[:-2]) * 1024
    else:
        return int(mem_str)


async def send_request(session, url):
    """단일 요청 전송"""
    log = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "device_id": "sensor-0001",
        "level": "INFO",
        "response_time": 1500,
        "temperature": 75.0,
        "message": "Test message"
    }
    start = time.perf_counter()
    try:
        async with session.post(url, json=log, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            await resp.text()
            elapsed = (time.perf_counter() - start) * 1000
            return {"success": resp.status == 200, "time_ms": elapsed}
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return {"success": False, "time_ms": elapsed}


async def run_load_test(url, total_requests, concurrency, label, name):
    """부하 테스트 실행 및 리소스 모니터링"""
    print(f"\n{'=' * 70}")
    print(f"{name} 테스트")
    print(f"{'=' * 70}")
    print(f"대상: {url}")
    print(f"요청 수: {total_requests}, 동시성: {concurrency}")
    print("-" * 70)
    
    # 초기 상태
    initial_pods = get_pod_count(label)
    print(f"\n초기 파드 수: {initial_pods}")
    
    # 리소스 모니터링 태스크
    resource_samples = []
    monitoring = True
    
    async def monitor_resources():
        while monitoring:
            metrics = get_pod_metrics(label)
            pod_count = get_pod_count(label)
            if metrics:
                total_cpu = sum(parse_cpu(m['cpu']) for m in metrics)
                total_memory = sum(parse_memory(m['memory']) for m in metrics)
                resource_samples.append({
                    'time': time.time(),
                    'pod_count': pod_count,
                    'total_cpu_m': total_cpu,
                    'total_memory_mb': total_memory,
                    'pods': metrics
                })
            await asyncio.sleep(2)
    
    monitor_task = asyncio.create_task(monitor_resources())
    
    # 부하 테스트
    print(f"\n부하 테스트 시작...")
    start_time = time.time()
    results = []
    
    async with aiohttp.ClientSession() as session:
        # 요청을 배치로 나누어 전송
        batch_size = concurrency
        for i in range(0, total_requests, batch_size):
            batch_count = min(batch_size, total_requests - i)
            tasks = [send_request(session, url) for _ in range(batch_count)]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            
            if (i + batch_count) % 1000 == 0:
                elapsed = time.time() - start_time
                print(f"  진행: {i + batch_count}/{total_requests} 요청 ({elapsed:.1f}초)")
    
    total_time = time.time() - start_time
    
    # 모니터링 중지
    monitoring = False
    await monitor_task
    
    # 최종 상태
    await asyncio.sleep(5)  # 마지막 메트릭 수집
    final_pods = get_pod_count(label)
    final_metrics = get_pod_metrics(label)
    
    # 결과 분석
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    if successful:
        times = [r["time_ms"] for r in successful]
        times_sorted = sorted(times)
        p95_idx = int(len(times_sorted) * 0.95)
        p99_idx = int(len(times_sorted) * 0.99)
        
        print(f"\n{'=' * 70}")
        print("테스트 결과")
        print(f"{'=' * 70}")
        
        print(f"\n📊 요청 통계:")
        print(f"  총 요청: {total_requests}")
        print(f"  성공: {len(successful)} ({len(successful)/total_requests*100:.1f}%)")
        print(f"  실패: {len(failed)} ({len(failed)/total_requests*100:.1f}%)")
        print(f"  총 시간: {total_time:.2f}초")
        print(f"  처리량: {len(successful)/total_time:.1f} req/s")
        
        print(f"\n⏱️ 응답 시간:")
        print(f"  평균: {statistics.mean(times):.2f}ms")
        print(f"  중앙값: {statistics.median(times):.2f}ms")
        print(f"  p95: {times_sorted[p95_idx]:.2f}ms")
        print(f"  p99: {times_sorted[p99_idx]:.2f}ms")
        print(f"  최대: {max(times):.2f}ms")
        
        print(f"\n🔧 리소스 사용:")
        print(f"  초기 파드: {initial_pods}")
        print(f"  최종 파드: {final_pods}")
        print(f"  최대 파드: {max(s['pod_count'] for s in resource_samples) if resource_samples else final_pods}")
        
        if resource_samples:
            avg_cpu = statistics.mean(s['total_cpu_m'] for s in resource_samples)
            max_cpu = max(s['total_cpu_m'] for s in resource_samples)
            avg_memory = statistics.mean(s['total_memory_mb'] for s in resource_samples)
            max_memory = max(s['total_memory_mb'] for s in resource_samples)
            
            print(f"  평균 CPU: {avg_cpu:.0f}m")
            print(f"  최대 CPU: {max_cpu:.0f}m")
            print(f"  평균 메모리: {avg_memory:.0f}Mi")
            print(f"  최대 메모리: {max_memory:.0f}Mi")
        
        if final_metrics:
            print(f"\n📦 최종 파드 상태:")
            for m in final_metrics:
                print(f"  {m['name']}: CPU {m['cpu']}, Memory {m['memory']}")
        
        print(f"\n{'=' * 70}")
        
        return {
            'name': name,
            'total_requests': total_requests,
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': len(successful)/total_requests*100,
            'total_time': total_time,
            'throughput': len(successful)/total_time,
            'avg_response_ms': statistics.mean(times),
            'p95_response_ms': times_sorted[p95_idx],
            'p99_response_ms': times_sorted[p99_idx],
            'initial_pods': initial_pods,
            'final_pods': final_pods,
            'max_pods': max(s['pod_count'] for s in resource_samples) if resource_samples else final_pods,
            'avg_cpu_m': statistics.mean(s['total_cpu_m'] for s in resource_samples) if resource_samples else 0,
            'max_cpu_m': max(s['total_cpu_m'] for s in resource_samples) if resource_samples else 0,
            'avg_memory_mb': statistics.mean(s['total_memory_mb'] for s in resource_samples) if resource_samples else 0,
            'max_memory_mb': max(s['total_memory_mb'] for s in resource_samples) if resource_samples else 0,
        }


async def compare(container_url, spinkube_url, total_requests, concurrency):
    """Container vs SpinKube 비교"""
    print("=" * 70)
    print("Container vs SpinKube 리소스 비교 테스트")
    print("=" * 70)
    
    # Container 테스트
    container_result = await run_load_test(
        container_url,
        total_requests,
        concurrency,
        "app=log-analyzer-container",
        "CONTAINER"
    )
    
    if not container_result:
        print("❌ Container 테스트 실패")
        return
    
    print("\n\n대기 중... (60초)")
    await asyncio.sleep(60)
    
    # SpinKube 테스트
    spinkube_result = await run_load_test(
        spinkube_url,
        total_requests,
        concurrency,
        "core.spinkube.dev/app-name=log-analyzer",
        "SPINKUBE"
    )
    
    if not spinkube_result:
        print("❌ SpinKube 테스트 실패")
        return
    
    # 비교 결과
    print("\n\n" + "=" * 70)
    print("비교 결과")
    print("=" * 70)
    
    print(f"\n{'항목':<20} {'Container':>20} {'SpinKube':>20} {'차이':>15}")
    print("-" * 70)
    
    def compare_metric(name, container_val, spinkube_val, unit="", reverse=False):
        if spinkube_val > 0:
            if reverse:
                ratio = container_val / spinkube_val
                better = "Container" if ratio < 1 else "SpinKube"
            else:
                ratio = spinkube_val / container_val
                better = "SpinKube" if ratio > 1 else "Container"
            diff = f"{ratio:.2f}x ({better})"
        else:
            diff = "N/A"
        print(f"{name:<20} {container_val:>19}{unit} {spinkube_val:>19}{unit} {diff:>15}")
    
    compare_metric("처리량", f"{container_result['throughput']:.1f}", f"{spinkube_result['throughput']:.1f}", " req/s")
    compare_metric("평균 응답시간", f"{container_result['avg_response_ms']:.1f}", f"{spinkube_result['avg_response_ms']:.1f}", "ms", reverse=True)
    compare_metric("p95 응답시간", f"{container_result['p95_response_ms']:.1f}", f"{spinkube_result['p95_response_ms']:.1f}", "ms", reverse=True)
    compare_metric("최대 파드 수", container_result['max_pods'], spinkube_result['max_pods'], "", reverse=True)
    compare_metric("평균 CPU", f"{container_result['avg_cpu_m']:.0f}", f"{spinkube_result['avg_cpu_m']:.0f}", "m", reverse=True)
    compare_metric("최대 CPU", f"{container_result['max_cpu_m']:.0f}", f"{spinkube_result['max_cpu_m']:.0f}", "m", reverse=True)
    compare_metric("평균 메모리", f"{container_result['avg_memory_mb']:.0f}", f"{spinkube_result['avg_memory_mb']:.0f}", "Mi", reverse=True)
    compare_metric("최대 메모리", f"{container_result['max_memory_mb']:.0f}", f"{spinkube_result['max_memory_mb']:.0f}", "Mi", reverse=True)
    
    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Container vs SpinKube 리소스 비교")
    parser.add_argument("--container-url", required=True, help="Container 서비스 URL")
    parser.add_argument("--spinkube-url", required=True, help="SpinKube 서비스 URL")
    parser.add_argument("--requests", type=int, default=10000, help="총 요청 수")
    parser.add_argument("--concurrency", type=int, default=500, help="동시 요청 수")
    
    args = parser.parse_args()
    asyncio.run(compare(args.container_url, args.spinkube_url, args.requests, args.concurrency))


if __name__ == "__main__":
    main()
