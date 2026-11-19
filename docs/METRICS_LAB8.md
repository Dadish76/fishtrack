
# FishTrack — Метрики приложения

## Назначение

FishTrack предоставляет метрики Prometheus через внутренний HTTP-адрес /metrics.

Метрики собираются отдельно с экземпляров app1 и app2.

## Метрики

### HTTP-запросы

fishtrack_http_requests_total

Counter с метками method, path и status.

### HTTP-ошибки

fishtrack_http_errors_total

Counter ответов 4xx и 5xx.

### Время ответа

fishtrack_http_request_duration_seconds

Histogram времени обработки HTTP-запросов в секундах.

### Состояние приложения

fishtrack_app_healthy

Gauge:
- 1 — последняя проверка PostgreSQL успешна.
- 0 — последняя проверка PostgreSQL неуспешна.

### Предметная метрика

fishtrack_trips_created_total

Counter успешно созданных рейсов через API и веб-интерфейс.

Счетчик хранится в памяти процесса и сбрасывается после перезапуска.

## Служебные адреса

/live — процесс FastAPI работает.

/health — соединение с PostgreSQL проверяется через SELECT 1.

/metrics — метрики приложения для Prometheus.

/version — версия работающего приложения.

## Безопасность

/metrics не должен публиковаться через внешний Nginx.

Prometheus должен обращаться к приложению по внутренней Docker-сети.

Нельзя использовать пароли, токены или пользовательские значения в метках метрик.

## Проверки

- make lint
- make sast
- make verify
- тесты /health
- тесты /metrics
- тест предметной метрики

## Проверка отказа PostgreSQL

При ошибке соединения /health возвращает HTTP 503.

При успешном восстановлении соединения /health снова возвращает HTTP 200.

## Следующий этап

Развертывание Prometheus, Grafana и инфраструктурных экспортеров.
