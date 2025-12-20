package main

import (
	"encoding/json"
	"fmt"
	"net/http"

	spinhttp "github.com/fermyon/spin/sdk/go/v2/http"
)

// LogEntry는 IoT 센서에서 전송되는 로그 구조체입니다.
type LogEntry struct {
	Level        string  `json:"level"`         // 로그 레벨: INFO, WARN, ERROR
	ResponseTime int     `json:"response_time"` // 응답 시간 (ms)
	DeviceID     string  `json:"device_id"`     // 디바이스 식별자
	Temperature  float64 `json:"temperature"`   // 온도 센서 값 (선택)
	Message      string  `json:"message"`       // 로그 메시지
}

// AnalysisResult는 로그 분석 결과를 담는 구조체입니다.
type AnalysisResult struct {
	Status   string   `json:"status"`   // OK, ALERT
	Alerts   []string `json:"alerts"`   // 발생한 알림 목록
	DeviceID string   `json:"device_id"`
}

// 임계값 상수 정의
const (
	ResponseTimeThreshold = 2000  // 응답 시간 임계값 (ms)
	TemperatureThreshold  = 80.0  // 온도 임계값 (°C)
)

func init() {
	spinhttp.Handle(func(w http.ResponseWriter, r *http.Request) {
		// POST 요청만 처리
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		// 요청 본문 파싱
		var log LogEntry
		if err := json.NewDecoder(r.Body).Decode(&log); err != nil {
			http.Error(w, fmt.Sprintf("Invalid JSON: %v", err), http.StatusBadRequest)
			return
		}

		// 로그 분석 수행
		result := analyzeLog(log)

		// 알림이 있으면 콘솔에 출력 (실제 환경에서는 SNS로 전송)
		if len(result.Alerts) > 0 {
			for _, alert := range result.Alerts {
				fmt.Printf("[ALERT] Device: %s - %s\n", result.DeviceID, alert)
			}
		}

		// 응답 반환
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(result)
	})
}

// analyzeLog는 로그를 분석하여 이상 징후를 탐지합니다.
func analyzeLog(log LogEntry) AnalysisResult {
	result := AnalysisResult{
		Status:   "OK",
		Alerts:   []string{},
		DeviceID: log.DeviceID,
	}

	// 1. ERROR 레벨 로그 감지
	if log.Level == "ERROR" {
		result.Alerts = append(result.Alerts, fmt.Sprintf("Error detected: %s", log.Message))
	}

	// 2. 응답 시간 임계값 초과 감지
	if log.ResponseTime > ResponseTimeThreshold {
		result.Alerts = append(result.Alerts, 
			fmt.Sprintf("High response time: %dms (threshold: %dms)", 
				log.ResponseTime, ResponseTimeThreshold))
	}

	// 3. 온도 임계값 초과 감지
	if log.Temperature > TemperatureThreshold {
		result.Alerts = append(result.Alerts,
			fmt.Sprintf("High temperature: %.1f°C (threshold: %.1f°C)",
				log.Temperature, TemperatureThreshold))
	}

	// 알림이 있으면 상태를 ALERT로 변경
	if len(result.Alerts) > 0 {
		result.Status = "ALERT"
	}

	return result
}

func main() {}
