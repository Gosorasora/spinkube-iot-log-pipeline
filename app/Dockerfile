# Spin 애플리케이션을 OCI 레지스트리에 푸시하기 위한 멀티스테이지 빌드
# 
# 사용법:
#   docker build -t your-registry/spinkube-log-analyzer:v1 .
#   docker push your-registry/spinkube-log-analyzer:v1

# Stage 1: TinyGo를 사용하여 Wasm 바이너리 빌드
FROM tinygo/tinygo:0.31.0 AS builder

WORKDIR /app

# Go 모듈 파일 복사 및 의존성 다운로드
COPY go.mod go.sum* ./
RUN go mod download

# 소스 코드 복사
COPY . .

# TinyGo로 WebAssembly 컴파일
RUN tinygo build -target=wasi -gc=leaking -no-debug -o main.wasm main.go

# Stage 2: Spin CLI를 사용하여 OCI 아티팩트 생성
FROM ghcr.io/fermyon/spin:v2.4.2 AS spin

WORKDIR /app

# 빌드된 Wasm 바이너리와 설정 파일 복사
COPY --from=builder /app/main.wasm .
COPY spin.toml .

# OCI 아티팩트로 패키징 (실제 푸시는 CI/CD에서 수행)
# spin registry push 명령어는 런타임에 실행해야 합니다.

# 최종 이미지는 Wasm 바이너리와 spin.toml만 포함
FROM scratch
COPY --from=builder /app/main.wasm /main.wasm
COPY --from=spin /app/spin.toml /spin.toml
