#!/usr/bin/env python3
"""
오토스케일링 속도 비교 테스트

Container vs SpinKube의 스케일 아웃 속도를 측정합니다.

측정 항목:
  1. 0→1 파드: 첫 파드 생성 시간 (콜드 스타트)
  2. 1→N 파드: 부하 증가 시 스케일 아웃 시간
  3. 파드별 Ready 시간
  4. 전체 스케일링 완료 시간

사용법:
  python scaling_test.py --target container --url http://localhost:80/analyze
  python scaling_test.py --target spinkube --url http://localhost:8081/analyze
"""

import argparse
import asyncio
import json
import subprocess
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


def get_pod_count(deployment_name):
    """현재 파드 수 조회"""
    # SpinApp의 경우 다른 레이블 사용
    if deployment_name == "log-analyzer":
        label = "core.spinkube.dev/app-name=log-analyzer"
    else:
        label = f"app={deployment_name}"
    
    output = run_kubectl(f"get pods -l {label} --no-headers")
    if not output:
        return 0
    return len([line for line in output.split('\n') if line.strip()])


def get_ready_pods(deployment_name):
    """Ready 상태 파드 수 조회"""
    # SpinApp의 경우 다른 레이블 사용
    if deployment_name == "log-analyzer":
        label = "core.spinkube.dev/app-name=log-analyzer"
    else:
        label = f"app={deployment_name}"
    
    output = run_kubectl(f"get pods -l {label} --no-headers")
    if not output:
        return 0
    ready_count = 0
    for line in output.split('\n'):
        if line.strip():
            parts = line.split()
            if len(parts) >= 2:
                ready_status = parts[1]  # 예: "1/1"
                current, total = ready_status.split('/')
                if current == total:
                    ready_count += 1
    return ready_count


def get_pod_ages(deployment_name):
    """파드별 생성 시간 조회"""
    # SpinApp의 경우 다른 레이블 사용
    if deployment_name == "log-analyzer":
        label = "core.spinkube.dev/app-name=log-analyzer"
    else:
        label = f"app={deployment_name}"
    
    output = run_kubectl(f"get pods -l {label} -o json")
    if not output:
        return []
    
    try:
        data = json.loads(output)
        ages = []
        for pod in data.get('items', []):
            name = pod['metadata']['name']
            creation = pod['metadata']['creationTimestamp']
            status = pod['status']['phase']
            
            # Ready 조건 확인
            ready = False
            for condition in pod['status'].get('conditions', []):
                if condition['type'] == 'Ready' and condition['status'] == 'True':
                    ready = True
                    break
            
            ages.append({
                'name': name,
                'created': creation,
                'status': status,
                'ready': ready
            })
        return ages
    except:
        return []


async def generate_load(url, duration_sec, concurrency):
    """부하 생성"""
    print(f"  부하 생성 중... (동시성: {concurrency}, 지속시간: {duration_sec}초)")
    
    async def send_request(session):
        log = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "device_id": "sensor-0001",
            "level": "INFO",
            "response_time": 1500,
            "temperature": 75.0,
            "message": "Test message"
        }
        try:
            async with session.post(url, json=log, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                await resp.text()
                return resp.status == 200
        except:
            return False
    
    start_time = time.time()
    success_count = 0
    total_count = 0
    
    async with aiohttp.ClientSession() as session:
        while time.time() - start_time < duration_sec:
            tasks = [send_request(session) for _ in range(concurrency)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count += sum(1 for r in results if r is True)
            total_count += len(results)
            await asyncio.sleep(0.1)
    
    print(f"  부하 생성 완료: {total_count} 요청, {success_count} 성공")


def monitor_scaling(deployment_name, initial_pods, target_pods, timeout_sec=300):
    """스케일링 모니터링"""
    print(f"\n스케일링 모니터링 시작: {initial_pods} → {target_pods} 파드")
    print("-" * 60)
    
    start_time = time.time()
    events = []
    last_pod_count = initial_pods
    last_ready_count = 0
    
    # 초기 상태 기록
    events.append({
        'time': 0,
        'total_pods': initial_pods,
        'ready_pods': get_ready_pods(deployment_name),
        'event': 'START'
    })
    
    while time.time() - start_time < timeout_sec:
        elapsed = time.time() - start_time
        current_pods = get_pod_count(deployment_name)
        ready_pods = get_ready_pods(deployment_name)
        
        # 파드 수 변화 감지
        if current_pods != last_pod_count:
            events.append({
                'time': elapsed,
                'total_pods': current_pods,
                'ready_pods': ready_pods,
                'event': f'POD_COUNT_CHANGED: {last_pod_count} → {current_pods}'
            })
            print(f"  [{elapsed:6.2f}s] 파드 수 변화: {last_pod_count} → {current_pods} (Ready: {ready_pods})")
            last_pod_count = current_pods
        
        # Ready 파드 수 변화 감지
        if ready_pods != last_ready_count:
            events.append({
                'time': elapsed,
                'total_pods': current_pods,
                'ready_pods': ready_pods,
                'event': f'READY_CHANGED: {last_ready_count} → {ready_pods}'
            })
            print(f"  [{elapsed:6.2f}s] Ready 파드: {last_ready_count} → {ready_pods}")
            last_ready_count = ready_pods
        
        # 목표 달성 확인
        if ready_pods >= target_pods:
            events.append({
                'time': elapsed,
                'total_pods': current_pods,
                'ready_pods': ready_pods,
                'event': 'TARGET_REACHED'
            })
            print(f"  [{elapsed:6.2f}s] ✅ 목표 달성: {ready_pods}/{target_pods} 파드 Ready")
            break
        
        time.sleep(1)
    
    total_time = time.time() - start_time
    
    # 최종 파드 상태
    pod_ages = get_pod_ages(deployment_name)
    
    return {
        'total_time': total_time,
        'events': events,
        'final_pods': last_pod_count,
        'final_ready': last_ready_count,
        'pod_details': pod_ages
    }


async def run_scaling_test(target_type, url, deployment_name):
    """스케일링 테스트 실행"""
    print("=" * 60)
    print(f"오토스케일링 속도 테스트: {target_type.upper()}")
    print("=" * 60)
    print(f"대상: {url}")
    print(f"Deployment: {deployment_name}")
    print("-" * 60)
    
    # 1단계: 초기 상태 확인
    print("\n[1/4] 초기 상태 확인...")
    initial_pods = get_pod_count(deployment_name)
    initial_ready = get_ready_pods(deployment_name)
    print(f"  현재 파드: {initial_pods} (Ready: {initial_ready})")
    
    if initial_pods == 0:
        print("  ⚠️  파드가 없습니다. Deployment를 먼저 배포하세요.")
        return
    
    # 2단계: 부하 생성 시작
    print("\n[2/4] 부하 생성 시작...")
    load_task = asyncio.create_task(generate_load(url, duration_sec=120, concurrency=100))
    
    # 잠시 대기 (부하가 쌓이도록)
    await asyncio.sleep(5)
    
    # 3단계: 스케일링 모니터링
    print("\n[3/4] 스케일링 모니터링...")
    result = monitor_scaling(deployment_name, initial_pods, target_pods=10, timeout_sec=180)
    
    # 4단계: 부하 생성 종료 대기
    print("\n[4/4] 부하 생성 종료 대기...")
    await load_task
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("테스트 결과")
    print("=" * 60)
    
    print(f"\n📊 스케일링 요약:")
    print(f"  초기 파드: {initial_pods}")
    print(f"  최종 파드: {result['final_pods']} (Ready: {result['final_ready']})")
    print(f"  총 소요 시간: {result['total_time']:.2f}초")
    
    # 첫 번째 스케일 아웃 시간
    first_scale = next((e for e in result['events'] if 'POD_COUNT_CHANGED' in e['event'] and e['total_pods'] > initial_pods), None)
    if first_scale:
        print(f"  첫 스케일 아웃: {first_scale['time']:.2f}초")
    
    # 첫 번째 새 파드 Ready 시간
    first_ready = next((e for e in result['events'] if 'READY_CHANGED' in e['event'] and e['ready_pods'] > initial_ready), None)
    if first_ready:
        print(f"  첫 파드 Ready: {first_ready['time']:.2f}초")
    
    print(f"\n📈 이벤트 타임라인:")
    for event in result['events']:
        print(f"  [{event['time']:6.2f}s] {event['event']} (Total: {event['total_pods']}, Ready: {event['ready_pods']})")
    
    print(f"\n🔍 파드 상세:")
    for pod in result['pod_details']:
        status_icon = "✅" if pod['ready'] else "⏳"
        print(f"  {status_icon} {pod['name']}: {pod['status']} (Created: {pod['created']})")
    
    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="오토스케일링 속도 비교 테스트")
    parser.add_argument("--target", choices=["container", "spinkube"], required=True, help="테스트 대상")
    parser.add_argument("--url", required=True, help="서비스 URL")
    
    args = parser.parse_args()
    
    # Deployment 이름 결정
    deployment_name = "log-analyzer-container" if args.target == "container" else "log-analyzer"
    
    asyncio.run(run_scaling_test(args.target, args.url, deployment_name))


if __name__ == "__main__":
    main()
