# Load test results

**Date:** 2026-10-29 (Asia/Shanghai)  
**Tool:** Locust 2.47.0 (locustfile.py)  
**Target:** http://127.0.0.1:5000 (Flask dev server, single process)  
**Profile:** 40 users, spawn-rate 10/s, run-time **45s**  
**Endpoints:** /shop (weight 5), /api/health (3), /shop/p/sticker-box (1)

## Summary

| Metric | Value |
|--------|------:|
| Total requests | 12,646 |
| Failures | **0 (0.00%)** |
| Aggregate RPS | **~287 req/s** |
| Avg latency | **~6.9 ms** |
| Median (p50) | **6 ms** |
| p95 | **14 ms** |
| p99 | **20 ms** |
| Max | **81 ms** |

## Per endpoint

| Endpoint | Reqs | Fail | RPS | Avg ms | p50 | p95 | Max |
|----------|-----:|-----:|----:|-------:|----:|----:|----:|
| GET /shop | 7112 | 0 | ~161 | 8.0 | 7 | 15 | 81 |
| GET /api/health | 4114 | 0 | ~93 | 4.9 | 4 | 10 | 36 |
| GET /shop/p/[slug] | 1420 | 0 | ~32 | 7.0 | 6 | 14 | 43 |

## Artifacts

- docs/load-raw_stats.csv / _stats_history.csv / _failures.csv
- docs/load-report.html (Locust HTML report)
- Reproduce: locust -f locustfile.py --host http://127.0.0.1:5000 --users 40 --spawn-rate 10 --run-time 45s --headless

## Notes

- Dev server is not production WSGI; numbers are a smoke-level stress ceiling on this box.
- Redis catalog cache was warm for /shop during the run (see smoke HIT/MISS).
- Concurrent checkout stress was covered in functional smoke (FOR UPDATE + Redis NX idempotency), not hammered here to avoid emptying demo stock.
