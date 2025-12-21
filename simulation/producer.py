#!/usr/bin/env python3
"""
IoT 로그 시뮬레이터 - 부하 테스트용 데이터 생성기

두 가지 모드 지원:
  1. HTTP 모드: 로컬 Spin 앱으로 직접 HTTP 요청 전송
  2. Event Hubs 모드: Azure Event Hubs로 데이터 전송

사용법:
  # HTTP 모드 (로컬 테스트)
  python producer.py --mode http --target http://localhost:3000/analyze --rate 100

  # Event Hubs 모드 (Azure 테스트)
  python producer.py --mode eventhub --connection-string "Endpoint=sb://..." --rate 1000

필요 패키지:
  pip install requests aiohttp azure-eventhub
"""

import argparse
import asyncio
import json
import random
import time
from datetime import datetime
from typing import Optional

# HTTP 요청용
try:
    import aiohttp
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Azure Event Hubs용
try:
    from azure.eventhub import EventHubProducerClient, EventData
    from azure.eventhub.aio import EventHubProducerClient as AsyncEventHubProducerClient
    EVENTHUB_AVAILABLE = True
except ImportError:
    EVENTHUB_AVAILABLE = False


# ============================================
# 로그 데이터 생성기
# ============================================
class LogGenerator:
    """IoT 센서 로그 데이터를 생성합니다."""

    DEVICE_IDS = [f"sensor-{i:04d}" for i in range(1, 101)]
    LOG_LEVELS = ["INFO", "WARN", "ERROR"]
    MESSAGES = {
        "INFO": ["정상 작동 중", "데이터 전송 완료", "센서 초기화 성공"],
        "WARN": ["배터리 부족", "신호 약함", "재시도 중"],
        "ERROR": ["연결 실패", "센서 오류", "타임아웃 발생"]
    }

    def __init__(self, error_rate: float = 0.1, high_latency_rate: float = 0.05):
        self.error_rate = error_rate
        self.high_latency_rate = high_latency_rate

    def generate(self) -> dict:
        """단일 로그 엔트리를 생성합니다."""
        rand = random.random()
        if rand < self.error_rate:
            level = "ERROR"
        elif rand < self.error_rate + 0.15:
            level = "WARN"
        else:
            level = "INFO"

        if random.random() < self.high_latency_rate:
            response_time = random.randint(2000, 5000)
        else:
            response_time = random.randint(50, 500)

        if random.random() < 0.05:
            temperature = random.uniform(80, 100)
        else:
            temperature = random.uniform(20, 75)

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "device_id": random.choice(self.DEVICE_IDS),
            "level": level,
            "response_time": response_time,
            "temperature": round(temperature, 1),
            "message": random.choice(self.MESSAGES[level])
        }

    def generate_batch(self, count: int) -> list:
        """여러 개의 로그 엔트리를 생성합니다."""
        return [self.generate() for _ in range(count)]


# ============================================
# HTTP 모드 - 로컬 Spin 앱 테스트
# ============================================
class HTTPProducer:
    """HTTP 요청으로 Spin 앱에 로그를 전송합니다."""

    def __init__(self, target_url: str):
        self.target_url = target_url
        self.generator = LogGenerator()
        self.stats = {"sent": 0, "success": 0, "failed": 0, "alerts": 0}

    async def send_async(self, session: aiohttp.ClientSession, log: dict) -> bool:
        """비동기 HTTP 요청을 전송합니다."""
        try:
            async with session.post(
                self.target_url,
                json=log,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                self.stats["sent"] += 1
                if response.status == 200:
                    self.stats["success"] += 1
                    result = await response.json()
                    if result.get("status") == "ALERT":
                        self.stats["alerts"] += 1
                    return True
                else:
                    self.stats["failed"] += 1
                    return False
        except Exception:
            self.stats["failed"] += 1
            return False

    async def run(self, rate: int, duration: int):
        """지정된 속도로 로그를 전송합니다."""
        print(f"🚀 HTTP 모드 시작: {self.target_url}")
        print(f"   속도: {rate} req/s, 지속시간: {duration}초")
        print("-" * 50)

        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            interval = 1.0 / rate

            while time.time() - start_time < duration:
                log = self.generator.generate()
                asyncio.create_task(self.send_async(session, log))
                await asyncio.sleep(interval)

                if self.stats["sent"] % rate == 0:
                    elapsed = time.time() - start_time
                    print(f"[{elapsed:.1f}s] 전송: {self.stats['sent']}, "
                          f"성공: {self.stats['success']}, "
                          f"실패: {self.stats['failed']}, "
                          f"알림: {self.stats['alerts']}")

            await asyncio.sleep(2)

        self._print_summary()

    def run_sync(self, rate: int, duration: int):
        """동기 방식으로 로그를 전송합니다."""
        print(f"🚀 HTTP 모드 (동기) 시작: {self.target_url}")

        start_time = time.time()
        interval = 1.0 / rate

        while time.time() - start_time < duration:
            log = self.generator.generate()
            try:
                response = requests.post(self.target_url, json=log, timeout=5)
                self.stats["sent"] += 1
                if response.status_code == 200:
                    self.stats["success"] += 1
                    if response.json().get("status") == "ALERT":
                        self.stats["alerts"] += 1
                else:
                    self.stats["failed"] += 1
            except Exception:
                self.stats["failed"] += 1

            time.sleep(interval)

        self._print_summary()

    def _print_summary(self):
        print("\n" + "=" * 50)
        print("📊 테스트 완료 요약")
        print(f"   총 전송: {self.stats['sent']}")
        print(f"   성공: {self.stats['success']}")
        print(f"   실패: {self.stats['failed']}")
        print(f"   알림 발생: {self.stats['alerts']}")
        print("=" * 50)


# ============================================
# Event Hubs 모드 - Azure 스트림 테스트
# ============================================
class EventHubProducer:
    """Azure Event Hubs로 로그를 전송합니다."""

    def __init__(self, connection_string: str, eventhub_name: str = None):
        if not EVENTHUB_AVAILABLE:
            raise ImportError("azure-eventhub가 설치되어 있지 않습니다: pip install azure-eventhub")

        self.connection_string = connection_string
        self.eventhub_name = eventhub_name
        self.generator = LogGenerator()
        self.stats = {"sent": 0, "success": 0, "failed": 0}

    def send_batch(self, logs: list) -> int:
        """배치로 Event Hub에 이벤트를 전송합니다."""
        try:
            producer = EventHubProducerClient.from_connection_string(
                conn_str=self.connection_string,
                eventhub_name=self.eventhub_name
            )

            with producer:
                event_data_batch = producer.create_batch()

                for log in logs:
                    try:
                        event_data_batch.add(EventData(json.dumps(log)))
                    except ValueError:
                        # 배치가 가득 찬 경우 전송 후 새 배치 생성
                        producer.send_batch(event_data_batch)
                        event_data_batch = producer.create_batch()
                        event_data_batch.add(EventData(json.dumps(log)))

                producer.send_batch(event_data_batch)

            self.stats["sent"] += len(logs)
            self.stats["success"] += len(logs)
            return len(logs)

        except Exception as e:
            print(f"❌ Event Hub 전송 실패: {e}")
            self.stats["failed"] += len(logs)
            return 0

    def run(self, rate: int, duration: int, batch_size: int = 100):
        """지정된 속도로 Event Hub에 로그를 전송합니다."""
        print(f"🚀 Event Hubs 모드 시작")
        print(f"   속도: {rate} events/s, 지속시간: {duration}초")
        print("-" * 50)

        start_time = time.time()
        batches_per_second = max(1, rate // batch_size)
        interval = 1.0 / batches_per_second
        actual_batch_size = rate // batches_per_second

        while time.time() - start_time < duration:
            logs = self.generator.generate_batch(actual_batch_size)
            self.send_batch(logs)

            elapsed = time.time() - start_time
            if int(elapsed) % 5 == 0 and self.stats["sent"] % (rate * 5) < actual_batch_size:
                print(f"[{elapsed:.1f}s] 전송: {self.stats['sent']}, "
                      f"성공: {self.stats['success']}, "
                      f"실패: {self.stats['failed']}")

            time.sleep(interval)

        self._print_summary()

    def _print_summary(self):
        print("\n" + "=" * 50)
        print("📊 Event Hubs 테스트 완료 요약")
        print(f"   총 전송: {self.stats['sent']}")
        print(f"   성공: {self.stats['success']}")
        print(f"   실패: {self.stats['failed']}")
        print("=" * 50)


# ============================================
# CLI 인터페이스
# ============================================
def main():
    parser = argparse.ArgumentParser(
        description="IoT 로그 시뮬레이터 - SpinKube 부하 테스트용"
    )
    parser.add_argument(
        "--mode",
        choices=["http", "eventhub"],
        default="http",
        help="전송 모드 (http: 로컬 테스트, eventhub: Azure 테스트)"
    )
    parser.add_argument(
        "--target",
        default="http://localhost:3000/analyze",
        help="HTTP 모드: Spin 앱 URL"
    )
    parser.add_argument(
        "--connection-string",
        default="",
        help="Event Hubs 모드: 연결 문자열"
    )
    parser.add_argument(
        "--eventhub-name",
        default="iot-log-stream",
        help="Event Hubs 모드: Event Hub 이름"
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=100,
        help="초당 요청/이벤트 수"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="테스트 지속 시간 (초)"
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="HTTP 모드: 동기 방식 사용 (디버깅용)"
    )

    args = parser.parse_args()

    if args.mode == "http":
        if not REQUESTS_AVAILABLE:
            print("❌ requests/aiohttp가 설치되어 있지 않습니다.")
            print("   pip install requests aiohttp")
            return

        producer = HTTPProducer(args.target)
        if args.sync:
            producer.run_sync(args.rate, args.duration)
        else:
            asyncio.run(producer.run(args.rate, args.duration))

    elif args.mode == "eventhub":
        if not EVENTHUB_AVAILABLE:
            print("❌ azure-eventhub가 설치되어 있지 않습니다.")
            print("   pip install azure-eventhub")
            return

        if not args.connection_string:
            print("❌ --connection-string 옵션이 필요합니다.")
            return

        producer = EventHubProducer(args.connection_string, args.eventhub_name)
        producer.run(args.rate, args.duration)


if __name__ == "__main__":
    main()
