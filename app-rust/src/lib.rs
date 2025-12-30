use spin_sdk::http::{IntoResponse, Request, Response, Method};
use spin_sdk::http_component;
use serde::{Deserialize, Serialize};

// 임계값 상수
const RESPONSE_TIME_THRESHOLD: u32 = 2000;
const TEMPERATURE_THRESHOLD: f32 = 80.0;

#[derive(Deserialize)]
struct Log {
    #[serde(default = "default_device_id")]
    device_id: String,
    level: Option<String>,
    response_time: Option<u32>,
    temperature: Option<f32>,
    message: Option<String>,
}

fn default_device_id() -> String {
    "unknown".to_string()
}

#[derive(Serialize)]
struct AnalysisResult {
    status: String,
    alerts: Vec<String>,
    device_id: String,
}

#[http_component]
fn handle_app_rust(req: Request) -> anyhow::Result<impl IntoResponse> {
    // POST 요청만 처리
    if *req.method() != Method::Post {
        return Ok(Response::builder()
            .status(405)
            .header("content-type", "application/json")
            .body(serde_json::to_vec(&serde_json::json!({"error": "Method not allowed"}))?)
            .build());
    }

    // JSON 파싱
    let body = req.body();
    let log: Log = match serde_json::from_slice(body) {
        Ok(l) => l,
        Err(e) => {
            return Ok(Response::builder()
                .status(400)
                .header("content-type", "application/json")
                .body(serde_json::to_vec(&serde_json::json!({"error": format!("Invalid JSON: {}", e)}))?)
                .build());
        }
    };

    // 로그 분석
    let (mut result, _is_alert) = analyze_log(&log);

    // 알림 출력 (Spin 로그로 기록 - stdout)
    if !result.alerts.is_empty() {
        for alert in &result.alerts {
            println!("[ALERT] Device: {} - {}", result.device_id, alert);
        }
    }

    Ok(Response::builder()
        .status(200)
        .header("content-type", "application/json")
        .body(serde_json::to_vec(&result)?)
        .build())
}

fn analyze_log(log: &Log) -> (AnalysisResult, bool) {
    let mut alerts = Vec::new();
    let mut is_alert = false;

    // ERROR 레벨 감지
    if let Some(level) = &log.level {
        if level == "ERROR" {
            let msg = log.message.as_deref().unwrap_or("");
            alerts.push(format!("Error detected: {}", msg));
            is_alert = true;
        }
    }

    // 응답 시간 임계값 초과
    if let Some(rt) = log.response_time {
        if rt > RESPONSE_TIME_THRESHOLD {
            alerts.push(format!(
                "High response time: {}ms (threshold: {}ms)",
                rt, RESPONSE_TIME_THRESHOLD
            ));
            is_alert = true;
        }
    }

    // 온도 임계값 초과
    if let Some(temp) = log.temperature {
        if temp > TEMPERATURE_THRESHOLD {
            alerts.push(format!(
                "High temperature: {}C (threshold: {}C)",
                temp, TEMPERATURE_THRESHOLD
            ));
            is_alert = true;
        }
    }

    let status = if is_alert { "ALERT" } else { "OK" };

    (
        AnalysisResult {
            status: status.to_string(),
            alerts,
            device_id: log.device_id.clone(),
        },
        is_alert,
    )
}
