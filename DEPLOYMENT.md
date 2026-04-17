# Deployment Information — Day 12 Lab

## Student

- **Name:** Trịnh Đức An
- **GitHub:** https://github.com/trhndan21/day12_ha-tang-cloud_va_deployment

---

## Public URL

```
https://day12lab06-production.up.railway.app
```

## Platform

**Railway** — Deployed via Docker (multi-stage build)

---

## Test Commands

### Health Check
```bash
curl https://day12lab06-production.up.railway.app/health
# Expected: {"status":"ok","uptime_seconds":...}
```

### Readiness Check
```bash
curl https://day12lab06-production.up.railway.app/ready
# Expected: {"status":"ready"}
```

### Authentication — No Key (Expect 401)
```bash
curl -X POST https://day12lab06-production.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
# Expected: {"detail":"Invalid or missing API Key..."}
```

### API Test — With Key (Expect 200)
```bash
curl -X POST https://day12lab06-production.up.railway.app/ask \
  -H "X-API-Key: 030621" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is production deployment?"}'
# Expected: {"question":"...","answer":"...","model":"...","timestamp":"..."}
```

### Rate Limiting Test (Expect 429 after 10 req/min)
```bash
for i in {1..15}; do
  curl -s -X POST https://day12lab06-production.up.railway.app/ask \
    -H "X-API-Key: 030621" \
    -H "Content-Type: application/json" \
    -d '{"question": "test '$i'"}' | python3 -m json.tool | grep -E "answer|detail"
done
```

---

## Architecture

```
Client
  │
  ▼
Railway Load Balancer
  │
  ▼
Agent Service (FastAPI + Uvicorn)
  - API Key Auth (X-API-Key header)
  - Rate Limiting (10 req/min per key)
  - Cost Guard ($10/month per key)
  - Conversation History
  │
  ▼
Redis Service (Internal, railway.internal)
  - Rate limit counters (Sorted Set)
  - Budget tracking (String + incrbyfloat)
  - Conversation history (List)
```

---

## Environment Variables Set on Railway

| Variable | Description |
|----------|-------------|
| `REDIS_URL` | Internal Redis URL from Railway Redis service |
| `AGENT_API_KEY` | API Key required to call `/ask` |
| `ENVIRONMENT` | `production` |
| `PORT` | `8000` (auto-set by Railway) |

---

## Production Readiness Checklist

- ✅ Dockerfile (multi-stage, < 500 MB)
- ✅ docker-compose.yml (agent + redis)
- ✅ .dockerignore
- ✅ .gitignore (includes .env)
- ✅ Health check endpoint (`GET /health`)
- ✅ Readiness endpoint (`GET /ready`)
- ✅ API Key authentication
- ✅ Rate limiting (10 req/min per user)
- ✅ Cost guard ($10/month per user, Redis-backed)
- ✅ Config từ environment variables
- ✅ Structured JSON logging
- ✅ Graceful shutdown (SIGTERM handler)
- ✅ Stateless design (state in Redis)
- ✅ No hardcoded secrets
- ✅ Deployed with public URL
