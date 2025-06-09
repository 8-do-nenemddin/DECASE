from fastapi import FastAPI, Form
from fastapi.responses import Response
from fastapi.responses import HTMLResponse, JSONResponse
import psutil
import os
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import socket

app = FastAPI()

# Initial state
data = {
    "server_status": "정상",
    "ready_status": "준비중"
}

# Prometheus Metrics 정의
cpu_usage_gauge = Gauge("cpu_usage_percent", "Current CPU usage percentage")
memory_total_gauge = Gauge("memory_total_bytes", "Total memory in bytes")
memory_available_gauge = Gauge("memory_available_bytes", "Available memory in bytes")
memory_used_gauge = Gauge("memory_used_bytes", "Used memory in bytes")
memory_free_gauge = Gauge("memory_free_bytes", "Free memory in bytes")

# HTML Template for root endpoint
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SKALA Kubernetes Practice</title>
    <script>
        document.addEventListener("DOMContentLoaded", () => {
            const serverStatus = document.getElementById("server_status");
            const readyStatus = document.getElementById("ready_status");
            const updateButton = document.getElementById("update_button");

            let initialServerStatus = serverStatus.value;
            let initialReadyStatus = readyStatus.value;

            function checkChanges() {
                if (serverStatus.value !== initialServerStatus || readyStatus.value !== initialReadyStatus) {
                    updateButton.disabled = false;
                } else {
                    updateButton.disabled = true;
                }
            }

            serverStatus.addEventListener("change", checkChanges);
            readyStatus.addEventListener("change", checkChanges);

            async function updateStatus() {
                const response = await fetch("/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/x-www-form-urlencoded"
                    },
                    body: new URLSearchParams({
                        "server_status": serverStatus.value,
                        "ready_status": readyStatus.value
                    })
                });

                if (response.ok) {
                    console.log("Status updated successfully");
                    initialServerStatus = serverStatus.value;
                    initialReadyStatus = readyStatus.value;
                    updateButton.disabled = true;
                } else {
                    console.error("Failed to update status");
                }
            }

            updateButton.addEventListener("click", (event) => {
                event.preventDefault();
                updateStatus();
            });
        });
    </script>
</head>
<body>
    <h1>SKALA kubernetes 실습 환경 접속을 환영합니다</h1>
    <p>web server 상태:</p>
    <form method="POST" action="javascript:void(0);">
        <label for="server_status">서버 상태:</label>
        <select id="server_status" name="server_status">
            <option value="정상" {% if server_status == '정상' %}selected{% endif %}>정상</option>
            <option value="장애" {% if server_status == '장애' %}selected{% endif %}>장애</option>
        </select>
        <br><br>
        <label for="ready_status">Ready 상태:</label>
        <select id="ready_status" name="ready_status">
            <option value="준비중" {% if ready_status == '준비중' %}selected{% endif %}>준비중</option>
            <option value="준비 완료" {% if ready_status == '준비 완료' %}selected{% endif %}>준비 완료</option>
        </select>
        <br><br>
        <button id="update_button" type="submit" disabled>Update</button>
    </form>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def read_root():
    return HTML_TEMPLATE.replace("{% if server_status == '정상' %}selected{% endif %}", "selected" if data["server_status"] == "정상" else "").replace("{% if server_status == '장애' %}selected{% endif %}", "selected" if data["server_status"] == "장애" else "").replace("{% if ready_status == '준비중' %}selected{% endif %}", "selected" if data["ready_status"] == "준비중" else "").replace("{% if ready_status == '준비 완료' %}selected{% endif %}", "selected" if data["ready_status"] == "준비 완료" else "")

@app.post("/")
def update_root(server_status: str = Form(...), ready_status: str = Form(...)):
    data["server_status"] = server_status
    data["ready_status"] = ready_status
    return {"message": "Status updated successfully"}

@app.get("/metrics")
def metrics():
    cpu_usage = psutil.cpu_percent()
    memory_info = psutil.virtual_memory()
    metrics_data = {
        "cpu_usage_percent": cpu_usage,
        "memory_total": memory_info.total,
        "memory_available": memory_info.available,
        "memory_used": memory_info.used,
        "memory_free": memory_info.free
    }
    return JSONResponse(metrics_data)

@app.get("/prometheus")
def prometheus_metrics():
    try:
        # 현재 시스템 상태 업데이트
        cpu_usage_gauge.set(psutil.cpu_percent())
        memory_info = psutil.virtual_memory()
        memory_total_gauge.set(memory_info.total)
        memory_available_gauge.set(memory_info.available)
        memory_used_gauge.set(memory_info.used)
        memory_free_gauge.set(memory_info.free)

        # Prometheus 형식으로 응답 반환
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/healthz")
def healthz():
    if data["server_status"] == "정상":
        return JSONResponse({"status": "UP"}, status_code=200)
    else:
        return JSONResponse({"status": "DOWN"}, status_code=400)

@app.get("/ready")
def ready():
    if data["ready_status"] == "준비 완료":
        return JSONResponse({"status": "READY"}, status_code=200)
    else:
        return JSONResponse({"status": "NOT READY"}, status_code=503)

@app.get("/info")
def info():
    skala_info = os.getenv("SKALA_INFO")
    user_info = os.getenv("USER_NAME")
    if skala_info:
        return JSONResponse({"info": skala_info, "user": user_info})
    else:
        return JSONResponse({"message": "SKALA_INFO environment variable is not set"}, status_code=404)

@app.get("/pod-ip")
def get_pod_ip():
    try:
        ip_address = socket.gethostbyname(socket.gethostname())
        return JSONResponse({"pod_ip": ip_address})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/hostname")
def get_hostname():
    try:
        hostname = socket.gethostname()
        return JSONResponse({"hostname": hostname})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()

    uvicorn.run(app, host="0.0.0.0", port=args.port)

