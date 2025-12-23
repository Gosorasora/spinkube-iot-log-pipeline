#!/usr/bin/env python3
"""
Container 버전 로그 분석 애플리케이션 (Flask)

SpinKube 버전과 동일한 로직을 Flask로 구현
성능 비교를 위한 컨테이너 기반 구현
"""

from flask import Flask, request, jsonify
import logging
import time

app = Flask(__name__)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 임계값 상수 (SpinKube 버전과 동일)
RESPONSE_TIME_THRESHOLD = 2000  # ms
TEMPERATURE_THRESHOLD = 80.0    # °C


@app.route('/health', methods=['GET'])
def health():
    """헬스 체크 엔드포인트"""
    return jsonify({"status": "healthy"}), 200


@app.route('/analyze', methods=['POST'])
def analyze():
    """
    로그 분석 엔드포인트
    
    Request Body:
    {
        "device_id": "sensor-0001",
        "level": "ERROR",
        "response_time": 2500,
        "temperature": 85.5,
        "message": "Connection failed"
    }
    
    Response:
    {
        "status": "ALERT" | "OK",
        "alerts": [...],
        "device_id": "sensor-0001"
    }
    """
    start_time = time.time()
    
    try:
        # 요청 데이터 파싱
        log = request.get_json()
        
        if not log:
            return jsonify({"error": "Invalid JSON"}), 400
        
        # 결과 초기화
        result = {
            "status": "OK",
            "alerts": [],
            "device_id": log.get("device_id", "unknown")
        }
        
        # 1. ERROR 레벨 감지
        if log.get("level") == "ERROR":
            message = log.get("message", "")
            result["alerts"].append(f"Error detected: {message}")
        
        # 2. 응답 시간 임계값 체크
        response_time = log.get("response_time", 0)
        if response_time > RESPONSE_TIME_THRESHOLD:
            result["alerts"].append(
                f"High response time: {response_time}ms (threshold: {RESPONSE_TIME_THRESHOLD}ms)"
            )
        
        # 3. 온도 임계값 체크
        temperature = log.get("temperature", 0)
        if temperature > TEMPERATURE_THRESHOLD:
            result["alerts"].append(
                f"High temperature: {temperature}C (threshold: {TEMPERATURE_THRESHOLD}C)"
            )
        
        # 알림이 있으면 상태를 ALERT로 변경
        if result["alerts"]:
            result["status"] = "ALERT"
        
        # 처리 시간 로깅
        processing_time = (time.time() - start_time) * 1000
        logger.info(f"Processed {result['device_id']} in {processing_time:.2f}ms - Status: {result['status']}")
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/', methods=['GET'])
def root():
    """루트 엔드포인트"""
    return jsonify({
        "service": "Log Analyzer (Container)",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "analyze": "/analyze (POST)"
        }
    }), 200


if __name__ == '__main__':
    logger.info("Starting Log Analyzer (Container version)")
    logger.info(f"Response time threshold: {RESPONSE_TIME_THRESHOLD}ms")
    logger.info(f"Temperature threshold: {TEMPERATURE_THRESHOLD}°C")
    
    # 프로덕션에서는 gunicorn 사용 권장
    app.run(host='0.0.0.0', port=80, debug=False)
