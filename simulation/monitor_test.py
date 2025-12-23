#!/usr/bin/env python3
"""
부하 테스트 + 실시간 리소스 모니터링

사용법:
  python monitor_test.py
"""

import asyncio
import subprocess
import time
import json
import random
from datetime import datetime

try:
    import aiohttp
except ImportError:
    print("pip install aiohttp")
    exit(1)


def get_pod_resources():
    """kubectl top pods로 리소스 사용량 조회"""
    try:
        result = subprocess.run(
            ["kubectl", "top", "pods", "-l", "core.spinkube.dev/app-name=log-analyzer", "--no-headers"],
            capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.strip().split("\n")
        pods = []
        for line in lines:
            if line:
                parts = line.split()
                if len(parts) >= 3:
                    pods.append({
                        "name": parts[0],
                        "cpu": parts[1],
                        "memory": parts[2]
                    })
        return pods
    except:
        return []


def generate_log():
    levels = ["INFO", "WARN", "ERROR"]
    return {
        "device_id": f"sensor-{random.randint(1, 1000):04d}",
        "level": random.choices(levels, weights=[0.7, 0.2, 0.1])[0],
        "response_time": random.randint(100, 3000),
        "temperature": random.uniform(20, 90),
    }


async def send_requests(url, count, concurrency):
    """비동기 요청 전송"""
    semaphore = asyncio.Semaphore(concurrency)
    results = {"success": 0, "failed": 0, "times": []}
    
    async def send_one(session):
        async with semaphore:
            start = time.perf_counter()
            try:
                async with session.post(url, json=generate_log(), timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    await resp.text()
                    elapsed = (time.perf_counter() - start) * 1000
                    if resp.status == 200:
                        results["success"] += 1
                    else:
                        results["failed"] += 1
                    results["times"].append(elapsed)
            except:
                results["failed"] += 1
    
    # 세션을 한 번만 생성하고 재사용
    async with aiohttp.ClientSession() as session:
        tasks = [send_one(session) for _ in range(count)]
        await asyncio.gather(*tasks)
    return results


async def main():
    url = "http://localhost:8081/analyze"
    
    print("=" * 70)
    print("SpinKube 부하 테스트 + 리소스 모니터링")
    print("=" * 70)
    
    # 초기 상태
    print("\n[초기 상태]")
    pods = get_pod_resources()
    for pod in pods:
        print(f"  {pod['name']}: CPU={pod['cpu']}, Memory={pod['memory']}")
    
    # 테스트 단계
    stages = [
        {"name": "저부하", "requests": 500, "concurrency": 50},
        {"name": "중부하", "requests": 5000, "concurrency": 500},
        {"name": "고부하", "requests": 15000, "concurrency": 1000},
    ]
    
    all_results = []
    
    for stage in stages:
        print(f"\n{'='*70}")
        print(f"[{stage['name']}] {stage['requests']} 요청, 동시성 {stage['concurrency']}")
        print("-" * 70)
        
        start = time.perf_counter()
        results = await send_requests(url, stage["requests"], stage["concurrency"])
        elapsed = time.perf_counter() - start
        
        # 결과 출력
        times = results["times"]
        if times:
            avg = sum(times) / len(times)
            p99 = sorted(times)[int(len(times) * 0.99)]
            throughput = stage["requests"] / elapsed
            
            print(f"  성공: {results['success']}, 실패: {results['failed']}")
            print(f"  평균 응답: {avg:.2f}ms, p99: {p99:.2f}ms")
            print(f"  처리량: {throughput:.1f} req/s")
            
            all_results.append({
                "stage": stage["name"],
                "avg_ms": avg,
                "p99_ms": p99,
                "throughput": throughput,
                "success_rate": results["success"] / stage["requests"] * 100
            })
        
        # 리소스 확인
        await asyncio.sleep(1)
        pods = get_pod_resources()
        print(f"  리소스 사용량:")
        for pod in pods:
            print(f"    {pod['name']}: CPU={pod['cpu']}, Memory={pod['memory']}")
    
    # 최종 요약
    print("\n" + "=" * 70)
    print("최종 요약")
    print("=" * 70)
    print(f"{'단계':<12} {'평균(ms)':<12} {'p99(ms)':<12} {'처리량':<15} {'성공률':<10}")
    print("-" * 70)
    for r in all_results:
        print(f"{r['stage']:<12} {r['avg_ms']:<12.2f} {r['p99_ms']:<12.2f} {r['throughput']:<15.1f} {r['success_rate']:<10.1f}%")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
