#!/usr/bin/env python3
"""
SpinKube 성능 벤치마크 스크립트

측정 항목:
  1. 응답 시간 (평균, 최소, 최대, p95, p99)
  2. 처리량 (requests/sec)
  3. 성공률

사용법:
  python benchmark.py --target http://localhost:3001/analyze --requests 1000 --concurrency 10
"""

import argparse
import asyncio
import json
import random
import statistics
import time
from datetime import datetime

try:
    import aiohttp
except ImportError:
    print("aiohttp 필요: pip install aiohttp")
    exit(1)


def generate_log():
    """테스트용 로그 데이터 생성"""
    levels = ["INFO", "WARN", "ERROR"]
    level = random.choices(levels, weights=[0.7, 0.2, 0.1])[0]
    
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "device_id": f"sensor-{random.randint(1, 1000):04d}",
        "level": level,
        "response_time": random.randint(100, 3000),
        "temperature": random.uniform(20, 90),
        "message": f"Test message {random.randint(1, 100)}"
    }


async def send_request(session, url, semaphore):
    """단일 요청 전송 및 응답 시간 측정"""
    async with semaphore:
        log = generate_log()
        start = time.perf_counter()
        try:
            async with session.post(url, json=log, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                await resp.text()
                elapsed = (time.perf_counter() - start) * 1000  # ms
                return {"success": resp.status == 200, "time_ms": elapsed, "status": resp.status}
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return {"success": False, "time_ms": elapsed, "error": str(e)}


async def run_benchmark(url, total_requests, concurrency):
    """벤치마크 실행"""
    print("=" * 60)
    print("SpinKube 성능 벤치마크")
    print("=" * 60)
    print(f"대상: {url}")
    print(f"총 요청: {total_requests}")
    print(f"동시성: {concurrency}")
    print("-" * 60)
    
    semaphore = asyncio.Semaphore(concurrency)
    results = []
    
    async with aiohttp.ClientSession() as session:
        # 워밍업 (콜드 스타트 측정용)
        print("\n[1/3] 워밍업 (콜드 스타트 측정)...")
        warmup_results = []
        for i in range(5):
            result = await send_request(session, url, asyncio.Semaphore(1))
            warmup_results.append(result)
            print(f"  요청 {i+1}: {result['time_ms']:.2f}ms")
        
        # 메인 벤치마크
        print(f"\n[2/3] 메인 벤치마크 ({total_requests} 요청)...")
        start_time = time.perf_counter()
        
        tasks = [send_request(session, url, semaphore) for _ in range(total_requests)]
        results = await asyncio.gather(*tasks)
        
        total_time = time.perf_counter() - start_time
    
    # 결과 분석
    print("\n[3/3] 결과 분석...")
    
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    times = [r["time_ms"] for r in successful]
    
    if times:
        times_sorted = sorted(times)
        p95_idx = int(len(times_sorted) * 0.95)
        p99_idx = int(len(times_sorted) * 0.99)
        
        print("\n" + "=" * 60)
        print("벤치마크 결과")
        print("=" * 60)
        
        print(f"\n📊 요청 통계:")
        print(f"  총 요청: {total_requests}")
        print(f"  성공: {len(successful)} ({len(successful)/total_requests*100:.1f}%)")
        print(f"  실패: {len(failed)} ({len(failed)/total_requests*100:.1f}%)")
        
        print(f"\n⏱️ 응답 시간:")
        print(f"  평균: {statistics.mean(times):.2f}ms")
        print(f"  최소: {min(times):.2f}ms")
        print(f"  최대: {max(times):.2f}ms")
        print(f"  중앙값: {statistics.median(times):.2f}ms")
        print(f"  표준편차: {statistics.stdev(times):.2f}ms" if len(times) > 1 else "")
        print(f"  p95: {times_sorted[p95_idx]:.2f}ms")
        print(f"  p99: {times_sorted[p99_idx]:.2f}ms")
        
        print(f"\n🚀 처리량:")
        print(f"  총 시간: {total_time:.2f}초")
        print(f"  처리량: {total_requests/total_time:.2f} req/s")
        
        print(f"\n🔥 콜드 스타트 (워밍업):")
        warmup_times = [r["time_ms"] for r in warmup_results if r["success"]]
        if warmup_times:
            print(f"  첫 번째 요청: {warmup_times[0]:.2f}ms")
            print(f"  평균: {statistics.mean(warmup_times):.2f}ms")
        
        # 히스토그램 (간단한 텍스트 버전)
        print(f"\n📈 응답 시간 분포:")
        buckets = [10, 20, 50, 100, 200, 500, 1000]
        for i, bucket in enumerate(buckets):
            prev = buckets[i-1] if i > 0 else 0
            count = len([t for t in times if prev < t <= bucket])
            bar = "█" * (count * 50 // len(times)) if times else ""
            print(f"  {prev:4d}-{bucket:4d}ms: {bar} ({count})")
        count = len([t for t in times if t > buckets[-1]])
        bar = "█" * (count * 50 // len(times)) if times else ""
        print(f"  {buckets[-1]:4d}ms+   : {bar} ({count})")
        
        print("\n" + "=" * 60)
    else:
        print("❌ 성공한 요청이 없습니다.")


def main():
    parser = argparse.ArgumentParser(description="SpinKube 성능 벤치마크")
    parser.add_argument("--target", default="http://localhost:3001/analyze", help="대상 URL")
    parser.add_argument("--requests", type=int, default=1000, help="총 요청 수")
    parser.add_argument("--concurrency", type=int, default=10, help="동시 요청 수")
    
    args = parser.parse_args()
    asyncio.run(run_benchmark(args.target, args.requests, args.concurrency))


if __name__ == "__main__":
    main()
