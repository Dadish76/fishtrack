from prometheus_client import Counter, Gauge, Histogram

# Общее количество HTTP-запросов.
HTTP_REQUESTS = Counter(
    "fishtrack_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

# Количество ошибочных HTTP-ответов (4xx и 5xx).
HTTP_ERRORS = Counter(
    "fishtrack_http_errors_total",
    "Total HTTP errors",
    ["method", "path", "status"],
)

# Длительность обработки запросов в секундах.
HTTP_DURATION = Histogram(
    "fishtrack_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
        float("inf"),
    ),
)

# 1 — БД доступна, 0 — БД недоступна.
APP_HEALTH = Gauge(
    "fishtrack_app_healthy",
    "Application readiness (1=healthy, 0=unhealthy)",
)

# Предметная метрика: число успешно созданных рейсов.
TRIPS_CREATED = Counter(
    "fishtrack_trips_created_total",
    "Total successfully created trips",
)
