from spin_sdk.http import IncomingHandler, Request, Response
import json

# 임계값 상수
RESPONSE_TIME_THRESHOLD = 2000
TEMPERATURE_THRESHOLD = 80.0


class IncomingHandler(IncomingHandler):
    def handle_request(self, request: Request) -> Response:
        # POST 요청만 처리
        if request.method != "POST":
            return Response(
                405,
                {"content-type": "application/json"},
                bytes(json.dumps({"error": "Method not allowed"}), "utf-8")
            )
        
        try:
            # JSON 파싱
            body = request.body.decode("utf-8")
            log = json.loads(body)
            
            # 로그 분석
            result = self.analyze_log(log)
            
            # 알림 출력 (Spin 로그로 기록)
            if result["alerts"]:
                for alert in result["alerts"]:
                    print(f"[ALERT] Device: {result['device_id']} - {alert}")
            
            return Response(
                200,
                {"content-type": "application/json"},
                bytes(json.dumps(result), "utf-8")
            )
        except json.JSONDecodeError as e:
            return Response(
                400,
                {"content-type": "application/json"},
                bytes(json.dumps({"error": f"Invalid JSON: {str(e)}"}), "utf-8")
            )
        except Exception as e:
            return Response(
                500,
                {"content-type": "application/json"},
                bytes(json.dumps({"error": str(e)}), "utf-8")
            )

    def analyze_log(self, log: dict) -> dict:
        """로그를 분석하여 이상 징후를 탐지합니다."""
        result = {
            "status": "OK",
            "alerts": [],
            "device_id": log.get("device_id", "unknown")
        }
        
        # ERROR 레벨 감지
        if log.get("level") == "ERROR":
            result["alerts"].append(f"Error detected: {log.get('message', '')}")
        
        # 응답 시간 임계값 초과
        response_time = log.get("response_time", 0)
        if response_time > RESPONSE_TIME_THRESHOLD:
            result["alerts"].append(
                f"High response time: {response_time}ms (threshold: {RESPONSE_TIME_THRESHOLD}ms)"
            )
        
        # 온도 임계값 초과
        temperature = log.get("temperature", 0)
        if temperature > TEMPERATURE_THRESHOLD:
            result["alerts"].append(
                f"High temperature: {temperature}C (threshold: {TEMPERATURE_THRESHOLD}C)"
            )
        
        # 알림이 있으면 상태 변경
        if result["alerts"]:
            result["status"] = "ALERT"
        
        return result
