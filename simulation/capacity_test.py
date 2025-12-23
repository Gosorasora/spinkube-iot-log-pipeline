#!/usr/bin/env python3
"""
단일 파드 처리 용량 테스트

단일 컨테이너/SpinKube 파드가 처리할 수 있는 최대 요청 수를 찾습니다.
동시성을 점진적으로 증가시키며 응답 시간과 성공률을 측정합니다.

사용법:
  python capacity_test.py --url http://localhost:8082/analyze --name container
"""

import argparse
import asyncio
import statistics
import time
from datetime import datetime

try:
    import aiohttp
except ImportError:
    print("aiohttp 필요: pip install aiohttp")
    exit(1)


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
        return {"success": False, "time_ms": elapsed, "error": str(e)}


async def test_concurrency(url, concurrency, duration_sec=30):
    """특정 동시성 레벨에서 테스트"""
    print(f"\n동시성 {concurrency} 테스트 중... ({duration_sec}초)")
    
    results = []
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        while time.time() - start_time < duration_sec:
            tasks = [send_request(session, url) for _ in range(concurrency)]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            await asyncio.sleep(0.01)  # 짧은 대기
    
    total_time = time.time() - start_time
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    if successful:
        times = [r["time_ms"] for r in successful]
        return {
            "concurrency": concurrency,
            "total_requests": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(results) * 100,
            "throughput": len(successful) / total_time,
            "avg_response_ms": statistics.mean(times),
            "p95_response_ms": sorted(times)[int(len(times) * 0.95)],
            "p99_response_ms": sorted(times)[int(len(times) * 0.99)],
            "max_response_ms": max(times)
        }
    else:
        return {
            "concurrency": concurrency,
            "total_requests": len(results),
            "successful": 0,
            "failed": len(failed),
            "success_rate": 0,
            "throughput": 0,
            "avg_response_ms": 0,
            "p95_response_ms": 0,
            "p99_response_ms": 0,
            "max_response_ms": 0
        }


async def find_capacity(url, name):
    """처리 용량 찾기"""
    print("=" * 70)
    print(f"단일 파드 처리 용량 테스트: {name.upper()}")
    print("=" * 70)
    print(f"대상: {url}")
    print("-" * 70)
    
    # 동시성 레벨을 점진적으로 증가
    concurrency_levels = [10, 20, 50, 100, 200, 300, 500, 1000]
    results = []
    
    for concurrency in concurrency_levels:
        result = await test_concurrency(url, concurrency, duration_sec=30)
        results.append(result)
        
        print(f"  동시성 {concurrency:4d}: "
              f"처리량 {result['throughput']:7.1f} req/s, "
              f"성공률 {result['success_rate']:5.1f}%, "
              f"평균 {result['avg_response_ms']:6.1f}ms, "
              f"p95 {result['p95_response_ms']:6.1f}ms")
        
        # 성공률이 95% 미만이면 중단
        if result['success_rate'] < 95:
            print(f"\n  ⚠️  성공률이 95% 미만으로 떨어졌습니다. 테스트 중단.")
            break
        
        # 응답 시간이 너무 길어지면 중단 (p95 > 1000ms)
        if result['p95_response_ms'] > 1000:
            print(f"\n  ⚠️  응답 시간이 너무 길어졌습니다. 테스트 중단.")
            break
    
    # 결과 분석
    print("\n" + "=" * 70)
    print("테스트 결과 요약")
    print("=" * 70)
    
    # 최대 처리량 찾기
    max_throughput = max(results, key=lambda x: x['throughput'])
    print(f"\n🚀 최대 처리량:")
    print(f"  동시성: {max_throughput['concurrency']}")
    print(f"  처리량: {max_throughput['throughput']:.1f} req/s")
    print(f"  평균 응답 시간: {max_throughput['avg_response_ms']:.1f}ms")
    print(f"  p95 응답 시간: {max_throughput['p95_response_ms']:.1f}ms")
    print(f"  성공률: {max_throughput['success_rate']:.1f}%")
    
    # 권장 동시성 (성공률 99% 이상, p95 < 500ms)
    good_results = [r for r in results if r['success_rate'] >= 99 and r['p95_response_ms'] < 500]
    if good_results:
        recommended = max(good_results, key=lambda x: x['throughput'])
        print(f"\n✅ 권장 동시성 (성공률 99%+, p95 < 500ms):")
        print(f"  동시성: {recommended['concurrency']}")
        print(f"  처리량: {recommended['throughput']:.1f} req/s")
        print(f"  평균 응답 시간: {recommended['avg_response_ms']:.1f}ms")
        print(f"  p95 응답 시간: {recommended['p95_response_ms']:.1f}ms")
    
    print("\n📊 전체 결과:")
    print(f"{'동시성':>8} {'처리량':>12} {'성공률':>8} {'평균':>10} {'p95':>10} {'p99':>10}")
    print("-" * 70)
    for r in results:
        print(f"{r['concurrency']:8d} {r['throughput']:10.1f}/s {r['success_rate']:7.1f}% "
              f"{r['avg_response_ms']:9.1f}ms {r['p95_response_ms']:9.1f}ms {r['p99_response_ms']:9.1f}ms")
    
    print("\n" + "=" * 70)
    
    return max_throughput


def main():
    parser = argparse.ArgumentParser(description="단일 파드 처리 용량 테스트")
    parser.add_argument("--url", required=True, help="서비스 URL")
    parser.add_argument("--name", required=True, help="테스트 이름 (container/spinkube)")
    
    args = parser.parse_args()
    asyncio.run(find_capacity(args.url, args.name))


if __name__ == "__main__":
    main()
