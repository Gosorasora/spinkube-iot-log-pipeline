#!/usr/bin/env python3
import asyncio
import aiohttp
import time
import subprocess
import os
import json
import statistics
import signal

# 설정
PYTHON_APP_DIR = "app"
RUST_APP_DIR = "app-rust"
PYTHON_PORT = 3001
RUST_PORT = 3002
REQUESTS = 1000
CONCURRENCY = 50

async def measure_performance(url, label):
    print(f"\n⚡ {label} 성능 측정 중... (요청: {REQUESTS}, 동시성: {CONCURRENCY})")
    
    times = []
    errors = 0
    start_total = time.perf_counter()
    
    async def fetch(session):
        nonlocal errors
        log = {
            "device_id": "bench-001",
            "level": "INFO",
            "response_time": 100,
            "temperature": 25.0
        }
        try:
            start = time.perf_counter()
            async with session.post(url, json=log) as response:
                await response.text()
                if response.status == 200:
                    times.append((time.perf_counter() - start) * 1000)
                else:
                    errors += 1
        except Exception:
            errors += 1

    async with aiohttp.ClientSession() as session:
        tasks = []
        completed = 0
        print(f"    [Progress] 0/{REQUESTS}", end="", flush=True)
        
        for _ in range(REQUESTS):
            tasks.append(fetch(session))
            if len(tasks) >= CONCURRENCY:
                await asyncio.gather(*tasks)
                completed += len(tasks)
                # 진행률 갱신
                print(f"\r    [Progress] {completed}/{REQUESTS} |{'#' * (completed // 50)}{'.' * ((REQUESTS - completed) // 50)}|", end="", flush=True)
                tasks = []
        if tasks:
            await asyncio.gather(*tasks)
            completed += len(tasks)
            print(f"\r    [Progress] {completed}/{REQUESTS} |{'#' * (completed // 50)}{'.' * ((REQUESTS - completed) // 50)}|", end="", flush=True)
    print() # 줄바꿈
            
    total_time = time.perf_counter() - start_total
    
    if not times:
        return None

    return {
        "avg": statistics.mean(times),
        "min": min(times),
        "max": max(times),
        "p95": sorted(times)[int(len(times) * 0.95)],
        "rps": len(times) / total_time,
        "errors": errors
    }

def get_file_size(path):
    try:
        size = os.path.getsize(path)
        return size / (1024 * 1024) # MB
    except FileNotFoundError:
        return 0

def run_spin_up(directory, port):
    print(f"🚀 {directory} 시작 중 (Port: {port})...")
    # spin up 명령어 실행
    proc = subprocess.Popen(
        ["spin", "up", "--listen", f"127.0.0.1:{port}"],
        cwd=directory,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid 
    )
    time.sleep(2) # 서버 시작 대기
    return proc

def main():
    print("=" * 60)
    print("🐍 Python vs 🦀 Rust : WebAssembly 성능 대결")
    print("=" * 60)

    # 1. 파일 크기 비교
    py_wasm = os.path.join(PYTHON_APP_DIR, "app.wasm")
    rust_wasm = os.path.join(RUST_APP_DIR, "target/wasm32-wasip1/release/app_rust.wasm")
    
    py_size = get_file_size(py_wasm)
    rust_size = get_file_size(rust_wasm)
    
    print(f"\n📦 바이너리 크기 (Wasm 파일)")
    print(f"   Python: {py_size:.2f} MB")
    print(f"   Rust:   {rust_size:.2f} MB")
    if py_size > 0 and rust_size > 0:
        print(f"   ✨ Rust가 {py_size / rust_size:.1f}배 더 작음")

    # 2. 서버 실행
    py_proc = run_spin_up(PYTHON_APP_DIR, PYTHON_PORT)
    rust_proc = run_spin_up(RUST_APP_DIR, RUST_PORT)

    try:
        # 3. 성능 측정
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        py_result = loop.run_until_complete(measure_performance(f"http://127.0.0.1:{PYTHON_PORT}/...", "Python (Wasm)"))
        rust_result = loop.run_until_complete(measure_performance(f"http://127.0.0.1:{RUST_PORT}/...", "Rust (Native Wasm)"))
        
        # 4. 결과 출력
        print("\n" + "=" * 60)
        print(f"{'Metric':<15} | {'Python (Wasm)':<15} | {'Rust (Native)':<15} | {'Diff'}")
        print("-" * 60)
        
        if py_result and rust_result:
            # Latency (Avg)
            diff_avg = py_result['avg'] / rust_result['avg']
            print(f"{'Avg Latency':<15} | {py_result['avg']:.2f} ms{'':<8} | {rust_result['avg']:.2f} ms{'':<8} | {diff_avg:.1f}x Faster")
            
            # Latency (P95)
            diff_p95 = py_result['p95'] / rust_result['p95']
            print(f"{'P95 Latency':<15} | {py_result['p95']:.2f} ms{'':<8} | {rust_result['p95']:.2f} ms{'':<8} | {diff_p95:.1f}x Faster")
            
            # RPS
            diff_rps = rust_result['rps'] / py_result['rps']
            print(f"{'Throughput':<15} | {int(py_result['rps']):,} req/s{'':<5} | {int(rust_result['rps']):,} req/s{'':<5} | {diff_rps:.1f}x Higher")
            
        print("=" * 60)
        
        if rust_result and py_result and rust_result['avg'] < py_result['avg']:
             print("\n🏆 결론: Rust가 앞도적으로 우세합니다.")
             print("   이것이 바로 '인터프리터 오버헤드'가 없는 Native Wasm의 성능입니다.")

    finally:
        # 정리
        os.killpg(os.getpgid(py_proc.pid), signal.SIGTERM)
        os.killpg(os.getpgid(rust_proc.pid), signal.SIGTERM)

if __name__ == "__main__":
    main()
