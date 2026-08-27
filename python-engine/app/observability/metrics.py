# Prometheus 指标定义
from __future__ import annotations

import os

import psutil
from prometheus_client import Counter, Gauge, Histogram, Info

# ── HTTP 请求级 ──
HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "path"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# ── LLM Gateway 级 ──
LLM_REQUESTS = Counter(
    "llm_requests_total",
    "Total LLM requests",
    ["provider", "model", "status"],
)
LLM_REQUEST_DURATION = Histogram(
    "llm_request_duration_seconds",
    "LLM request duration",
    ["provider", "model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)
LLM_TOKENS = Counter(
    "llm_tokens_total",
    "Total LLM tokens consumed",
    ["provider", "model", "direction"],
)
LLM_CACHE_HITS = Counter(
    "llm_cache_hits_total",
    "LLM cache hits",
    ["level"],  # l1 / l2 / l3
)
LLM_CACHE_MISSES = Counter("llm_cache_misses_total", "LLM cache misses")
LLM_CIRCUIT_STATE = Gauge(
    "llm_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open)",
    ["provider"],
)

# ── 预算级 ──
TOKEN_BUDGET_USED = Gauge(
    "token_budget_used",
    "Token budget used this month",
    ["tenant_id"],
)
TOKEN_BUDGET_LIMIT = Gauge(
    "token_budget_limit",
    "Token budget monthly limit",
    ["tenant_id"],
)

# ── 队列级 ──
QUEUE_DEPTH = Gauge(
    "queue_depth",
    "Task queue depth",
    ["stream"],
)
QUEUE_PROCESSING_DURATION = Histogram(
    "queue_processing_duration_seconds",
    "Task processing duration",
    ["task_type"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
)
QUEUE_DLQ_TOTAL = Counter(
    "queue_dlq_total",
    "Total tasks moved to dead letter queue",
    ["task_type"],
)
QUEUE_RETRY_TOTAL = Counter(
    "queue_retry_total",
    "Total tasks re-queued for retry",
    ["task_type"],
)

# ── 实例级 ──
INSTANCE_ACTIVE_REQUESTS = Gauge(
    "instance_active_requests",
    "Active requests on this instance",
)
INSTANCE_UPTIME = Gauge(
    "instance_uptime_seconds",
    "Instance uptime in seconds",
)
ENGINE_INFO = Info("engine", "Python AI Engine info")

# ── 系统资源指标 ──
PROCESS_CPU_PERCENT = Gauge(
    "process_cpu_percent",
    "Current CPU usage percentage",
)
PROCESS_MEMORY_RSS = Gauge(
    "process_memory_rss_bytes",
    "Resident set size in bytes",
)
PROCESS_MEMORY_VMS = Gauge(
    "process_memory_vms_bytes",
    "Virtual memory size in bytes",
)
PROCESS_THREADS = Gauge(
    "process_threads",
    "Number of threads",
)


def record_process_metrics():
    """记录进程资源使用指标"""
    try:
        process = psutil.Process(os.getpid())
        PROCESS_CPU_PERCENT.set(process.cpu_percent(interval=None))
        mem_info = process.memory_info()
        PROCESS_MEMORY_RSS.set(mem_info.rss)
        PROCESS_MEMORY_VMS.set(mem_info.vms)
        PROCESS_THREADS.set(process.num_threads())
    except Exception as e:
        # 静默失败，避免影响主流程
        pass
