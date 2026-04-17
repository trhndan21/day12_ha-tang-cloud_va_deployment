# Day 12 Lab - Mission Answers

> **Student Name:** Trịnh Đức An
> **Student ID:** (your student ID)
> **Date:** 2026-04-17

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found in `01-localhost-vs-production/develop/app.py`

1. **Hardcoded API Keys** (Line 21–22): `OPENAI_API_KEY` và `DATABASE_URL` được ghi trực tiếp vào code. Nếu push lên GitHub, thông tin nhạy cảm bị lộ ngay lập tức.
2. **Không có config management** (Line 25–26): Biến `DEBUG = True` và `MAX_TOKENS = 500` cứng trong code thay vì đọc từ environment variables. Không thể thay đổi hành vi mà không sửa code.
3. **Dùng `print()` thay vì proper logging** (Line 38–43): `print()` không có log level, không có timestamp, không thể filter. Đặc biệt nghiêm trọng khi print ra secret (`OPENAI_API_KEY`).
4. **Không có health check endpoint**: Platform không biết khi nào agent bị crash để tự động restart container.
5. **Port và host cứng** (Line 56–58): `host="localhost"` chỉ chạy được trên máy local, không thể nhận traffic từ bên ngoài. `port=8000` cứng, không đọc từ `PORT` env var mà platforms inject vào.

### Exercise 1.3: Comparison table

| Feature | Develop (Basic) | Production (Advanced) | Tại sao quan trọng? |
|---------|----------|------------|---------------------|
| Config | Hardcode trong code | Đọc từ env vars qua `pydantic-settings` | Tránh lộ secrets, dễ thay đổi mà không sửa code |
| Health check | ❌ Không có | ✅ `GET /health` + `GET /ready` | Platform tự restart khi crash; load balancer biết khi nào route traffic |
| Logging | `print()` — không có level | JSON structured logging với timestamp và log level | Dễ filter, search, và ingest vào ELK/Datadog trong production |
| Shutdown | Đột ngột (SIGKILL) | Graceful — hoàn thành request rồi mới tắt | Không mất request đang xử lý khi deploy phiên bản mới |
| Host | `localhost` — chỉ local | `0.0.0.0` — nhận traffic từ mọi interface | Container cần bind `0.0.0.0` để nhận traffic từ ngoài |
| Port | Cứng `8000` | Đọc từ `PORT` env var | Platforms như Railway inject `PORT` động |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions (`02-docker/develop/Dockerfile`)

1. **Base image:** `python:3.11-slim` — phiên bản slim nhẹ hơn so với full image
2. **Working directory:** `/app`
3. **Tại sao COPY requirements.txt trước?** Docker cache layer theo từng lệnh. Nếu `requirements.txt` không thay đổi, Docker tái dụng cache layer pip install mà không cần cài lại → build nhanh hơn nhiều.
4. **CMD vs ENTRYPOINT:** `ENTRYPOINT` định nghĩa process chính không thể override (dùng cho binary command), còn `CMD` cung cấp default arguments và có thể override khi `docker run`. Dùng kết hợp: `ENTRYPOINT ["python"]` + `CMD ["app.py"]`.

### Exercise 2.3: Image size comparison

| Version | Build type | Kích thước ước tính |
|---------|-----------|---------------------|
| Develop | Single-stage | ~900 MB |
| Production | Multi-stage | ~350 MB |
| **Chênh lệch** | | **~60% nhỏ hơn** |

Multi-stage build loại bỏ toàn bộ build tools (gcc, pip cache, build dependencies) không cần thiết ở runtime, chỉ giữ lại app code và wheels đã được compiled.

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- **Platform:** Railway
- **URL:** https://day12lab06-production.up.railway.app
- **Health check:** `curl https://day12lab06-production.up.railway.app/health`

**Test output:**
```json
{"status":"ok","uptime_seconds":556.52}
```

---

## Part 4: API Security

### Exercise 4.1–4.3: Security test results

**Không có API key → 401:**
```bash
curl -X POST https://day12lab06-production.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
# → {"detail":"Invalid or missing API Key. Please provide X-API-Key header."}
```

**Có API key hợp lệ → 200:**
```bash
curl -X POST https://day12lab06-production.up.railway.app/ask \
  -H "X-API-Key: 030621" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Docker?"}'
# → {"question":"...","answer":"...","model":"gpt-4o-mini","timestamp":"..."}
```

**Rate Limiting:** Sau 10 requests/phút → HTTP 429 `Rate limit exceeded`.

### Exercise 4.4: Cost guard implementation

Cost guard dùng Redis để track tổng chi phí của mỗi user theo tháng:
- Key pattern: `budget:{user_id}:{YYYY-MM}` → tự reset mỗi tháng
- Giới hạn: `$10/tháng/user` (cấu hình qua `MONTHLY_BUDGET_USD` env var)
- Mỗi request ước tính `$0.02` và cộng vào tổng
- Nếu vượt ngưỡng → HTTP 402 `Monthly budget exceeded`
- TTL của key: 32 ngày → tự động cleanup

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks

```python
@app.get("/health")  # Liveness probe — container còn sống?
def health():
    return {"status": "ok", "uptime_seconds": round(time.time() - START_TIME, 2)}

@app.get("/ready")  # Readiness probe — sẵn sàng nhận traffic?
def ready():
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    return {"status": "ready"}
```

### Exercise 5.2: Graceful shutdown

```python
def handle_exit(sig, frame):
    logger.info(json.dumps({"event": "exit_signal_received", "signal": sig}))

signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)
```

Uvicorn được cấu hình `timeout_graceful_shutdown=30` để hoàn thành các request đang xử lý trước khi tắt.

### Exercise 5.3: Stateless design

State được lưu trong Redis thay vì memory:
- **Conversation history:** `history:{user_id}` (Redis List, giới hạn 10 messages)
- **Rate limit counters:** `rate_limit:{user_id}` (Redis Sorted Set, sliding window 60s)
- **Budget tracking:** `budget:{user_id}:{month}` (Redis String, incrbyfloat)

→ Khi scale lên 3 instances, mọi instance đều đọc/ghi chung một Redis → stateless hoàn toàn.

### Exercise 5.4: Load balancing

```bash
docker compose up --scale agent=3
# Nginx phân tán requests theo round-robin
# Nếu một instance crash, Nginx tự chuyển sang instance khác
```

### Exercise 5.5: Stateless verification

Conversation history được lưu trong Redis với key `history:{user_id}`. Khi kill một container và gửi request tiếp theo đến container khác, history vẫn còn → stateless design hoạt động đúng.
