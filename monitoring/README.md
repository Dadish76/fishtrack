# Мониторинг FishTrack

Конфигурация наблюдаемости хранится в Git. Prometheus собирает метрики приложения и инфраструктуры, Grafana отображает их, а правила Prometheus обнаруживают проблемы. Для диагностики и восстановления используется [Runbook](../docs/observability-runbook.md).

## 1. Состав системы

| Компонент | Назначение | Версия образа |
|---|---|---|
| Prometheus | Сбор метрик и вычисление правил | `prom/prometheus:v3.13.5` |
| Grafana | Визуализация метрик | `grafana/grafana:13.3.2-ubuntu` |
| Node Exporter | Метрики Linux-узла | `quay.io/prometheus/node-exporter:v1.13.1` |
| cAdvisor | Метрики Docker-контейнеров | `ghcr.io/google/cadvisor:v0.61.1` |

Точные параметры запуска и версии задаются в `compose.yml`. Теги версий фиксированы, но не являются криптографической фиксацией образов по digest.

## 2. Структура конфигурации

```text
monitoring/
├── README.md
├── compose.yml
├── prometheus/
│   ├── prometheus.yml
│   └── rules/
│       └── fishtrack-alerts.yml
└── grafana/
    ├── dashboards/
    │   └── fishtrack-observability.json
    └── provisioning/
        ├── dashboards/
        │   └── fishtrack.yml
        └── datasources/
            └── prometheus.yml
```

Dashboard содержит 15 панелей и 18 запросов PromQL. Источник данных Prometheus имеет UID `fishtrack-prometheus`. Dashboard загружается автоматически из JSON, поэтому изменения необходимо вносить в версионируемый файл.

## 3. Предварительные условия

- Docker Desktop в режиме Linux-контейнеров, Docker Compose v2 и PowerShell; команды выполняются из корня репозитория.
- FishTrack уже развернут: `app1`, `app2`, `db` и `nginx` работают. Prometheus должен иметь доступ к `app1:8000` и `app2:8000` по общей Docker-сети.
- Внешняя Docker-сеть приложения существует. Ее имя задается переменной `FISHTRACK_NETWORK`.
- Пароль Grafana передается через `GRAFANA_ADMIN_PASSWORD`, а не хранится в Git.
- Порты 9090 и 3000 свободны на локальном адресе либо заняты уже работающими контейнерами этого же проекта мониторинга.

## 4. Запуск локального мониторинга

Проверить Docker context и доступность демона:

```powershell
docker context show
docker version
docker network ls
```

Для существующего изолированного стенда лабораторной работы имя сети — `fishtrack-lab8-20261125201915_internal`. Для нового развертывания следует выбрать фактическую сеть своего проекта.

```powershell
$env:FISHTRACK_NETWORK = "fishtrack-lab8-20261125201915_internal"
docker network inspect $env:FISHTRACK_NETWORK --format '{{.Name}}'
```

Передать пароль без его вывода в терминал:

```powershell
$grafanaPassword = Read-Host "Введите пароль Grafana" -AsSecureString
$env:GRAFANA_ADMIN_PASSWORD = [System.Net.NetworkCredential]::new("", $grafanaPassword).Password
Remove-Variable grafanaPassword
```

При первом запуске пароль используется для создания администратора Grafana. При существующем томе Grafana смена переменной окружения сама по себе не меняет уже сохраненный пароль пользователя.

```powershell
function mon8 {
    docker compose -p fishtrack-lab8-monitoring -f monitoring/compose.yml @args
}

mon8 config --quiet
mon8 run --rm --no-deps --entrypoint /bin/promtool prometheus check config /etc/prometheus/prometheus.yml
mon8 run --rm --no-deps --entrypoint /bin/promtool prometheus check rules /etc/prometheus/rules/fishtrack-alerts.yml
```

Только после успешных проверок и в нужном Docker context запустить мониторинг:

```powershell
mon8 up -d
mon8 ps
```

При открытии новой сессии PowerShell временные переменные и функцию `mon8` нужно задать заново. Не использовать `docker compose down -v` для штатного обновления: эта команда удаляет именованные тома проекта.

## 5. Проверка после запуска

| Точка доступа | Ожидаемый результат |
|---|---|
| `http://127.0.0.1:9090/-/ready` | HTTP 200 |
| `http://127.0.0.1:9090/targets` | 5 целей UP |
| `http://127.0.0.1:9090/alerts` | 5 правил, при нормальной работе Inactive |
| `http://127.0.0.1:3000/api/health` | HTTP 200, database: ok |
| `http://127.0.0.1:3000/d/fishtrack-observability/fishtrack-observability` | Dashboard FishTrack Observability |
| `http://127.0.0.1:18080/health` | HTTP 200 для текущего локального стенда |
| `http://127.0.0.1:18080/metrics` | HTTP 404 через Nginx |

В Grafana войти под пользователем `admin` с установленным паролем и выбрать фактический Compose-проект FishTrack. Проверить данные по обоим экземплярам, ресурсы узла и контейнеров, HTTP-метрики и предметную метрику.

Основные запросы Prometheus:

```promql
up{job="fishtrack"}
fishtrack_app_healthy{job="fishtrack"}
fishtrack_trips_created_total{job="fishtrack"}
```

В нормальном состоянии первые два запроса возвращают по две серии со значением 1. Метрика готовности отражает последнюю проверку `/health`; наличие метрик не гарантирует готовность приложения. При отсутствии пользовательских запросов задержка и доля ошибок могут быть неопределенными.

## 6. Правила обнаружения проблем

| Правило | Условие | Время удержания |
|---|---|---|
| `FishTrackInstanceDown` | `up` равен 0 для экземпляра FishTrack | 30 с |
| `FishTrackNotReady` | Готовность равна 0 при доступных метриках | 30 с |
| `FishTrackHighErrorRate` | Доля 5xx выше 5% при нагрузке не менее 0,1 запроса/с | 1 мин |
| `HostHighCPU` | CPU выше 80% | 2 мин |
| `HostHighMemory` | Использование RAM выше 85% | 2 мин |

Prometheus обнаруживает проблемы и показывает состояния Inactive, Pending и Firing. Отдельная доставка уведомлений через Alertmanager не настроена. Практически проверено правило `FishTrackNotReady` при остановке и восстановлении локальной PostgreSQL; остальные правила прошли проверку синтаксиса и вычисления.

## 7. Безопасность и хранение данных

- Конфигурации, правила и Dashboard хранятся в Git; реальные пароли, токены и содержимое локальных файлов секретов — вне репозитория.
- Prometheus и Grafana доступны через привязку портов к `127.0.0.1`. Анонимный доступ и самостоятельная регистрация в Grafana отключены. Nginx не публикует `/metrics` приложения.
- Для Prometheus и Grafana предусмотрены именованные тома `prometheus_data` и `grafana_data`; история Prometheus хранится 7 суток. Данные этих томов не включаются в Git.
- Экспортеры не публикуют порты на хост. cAdvisor работает в привилегированном режиме и имеет доступ к сокету Docker, что дает широкие полномочия даже при монтировании `:ro`. Допускать такой доступ следует только в доверенном окружении.
- После завершения работы с командами Compose можно удалить пароль из текущего окружения: `Remove-Item Env:GRAFANA_ADMIN_PASSWORD`. Для следующего запуска его потребуется снова передать. Административный доступ к Docker позволяет просматривать переменные контейнеров, поэтому он должен быть ограничен.

## 8. Проверка и перенос конфигурации

При изменении правил выполнить `promtool check rules` и `promtool check config`. При изменении Compose выполнить `docker compose ... config --quiet`. JSON Dashboard проверять на корректность синтаксиса и наличие всех запросов PromQL; выполнение запросов и доступность источника проверять после запуска Grafana.

Конфигурация протестирована локально на Docker Desktop / WSL2. Node Exporter отображает ресурсы Linux-окружения Docker, а не всего Windows-хоста. Параметр cAdvisor `--containerd=/rootfs/run/containerd/containerd.sock` соответствует проверенному локальному окружению. Перед переносом на app-server необходимо подтвердить фактические пути сокетов, наличие сети и DNS-имен `app1`/`app2`, доступность образов и правила доступа. Развертывание на app-server пока не подтверждено. При необходимости удаленного доступа к Grafana следует использовать SSH-туннель, не открывая порт мониторинга без защиты.

## Лабораторная работа №8 — наблюдаемость и эксплуатация

В проекте FishTrack реализованы структурированное
логирование, сбор метрик приложения и инфраструктуры,
визуализация в Grafana и автоматическое обнаружение проблем.

Проведен выпуск функционального изменения, выполнено
сравнение состояния локальной системы до и после выпуска,
расследован контролируемый отказ PostgreSQL.

По результатам инцидента улучшен процесс обнаружения
проблем: время срабатывания нового правила составило
30,129 секунды вместо 65,260 секунды.

### Эксплуатационная документация

- [Инструкция диагностики и восстановления](docs/observability-runbook.md)
- [Сравнение состояния до и после выпуска](docs/release-comparison.md)
- [Отчет об инциденте](docs/incident-postmortem.md)
- [Улучшение процесса обнаружения проблем](docs/detection-improvement.md)
- [Автоматические и организационные барьеры](docs/protective-barriers.md)
- [Первичные результаты экспериментов](docs/evidence/lab8/)