#!/usr/bin/env python3
"""
Spin 앱 모킹 서버 - 로컬 테스트용
실제 Wasm 앱과 동일한 로직으로 로그를 분석합니다.

사용법:
  python mock_server.py
  # 다른 터미널에서: python producer.py --mode http --rate 10 --duration 30
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json

# 임계값 상수
RESPONSE_TIME_THRESHOLD = 2000
TEMPERATURE_THRESHOLD = 80.0

class LogAnalyzerHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/analyze':
            self.send_error(404)
            return
        
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        
        try:
            log = json.loads(body)
            result = self.analyze_log(log)
            
            # 알림 출력
            if result['alerts']:
                for alert in result['alerts']:
                    print(f"🚨 [ALERT] Device: {result['device_id']} - {alert}")
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        except Exception as e:
            self.send_error(400, str(e))
    
    def analyze_log(self, log):
        result = {
            'status': 'OK',
            'alerts': [],
            'device_id': log.get('device_id', 'unknown')
        }
        
        # ERROR 레벨 감지
        if log.get('level') == 'ERROR':
            result['alerts'].append(f"Error detected: {log.get('message', '')}")
        
        # 응답 시간 임계값 초과
        if log.get('response_time', 0) > RESPONSE_TIME_THRESHOLD:
            result['alerts'].append(
                f"High response time: {log['response_time']}ms (threshold: {RESPONSE_TIME_THRESHOLD}ms)")
        
        # 온도 임계값 초과
        if log.get('temperature', 0) > TEMPERATURE_THRESHOLD:
            result['alerts'].append(
                f"High temperature: {log['temperature']}°C (threshold: {TEMPERATURE_THRESHOLD}°C)")
        
        if result['alerts']:
            result['status'] = 'ALERT'
        
        return result
    
    def log_message(self, format, *args):
        pass  # 기본 로그 비활성화

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 9090), LogAnalyzerHandler)
    print("🚀 Mock Log Analyzer 서버 시작: http://localhost:9090/analyze")
    print("   Ctrl+C로 종료")
    server.serve_forever()
