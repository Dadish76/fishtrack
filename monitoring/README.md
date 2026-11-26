# Мониторинг FishTrack на app-server

Основной стенд наблюдаемости запускается на Ubuntu VM `app-server` вместе с существующим проектом `fishtrack-staging` (app1, app2, db, nginx). Отдельная db-server не нужна. Windows/Docker Desktop — только прежний локальный эксперимент; данные двух стендов не смешиваются. Исторические отчеты лабораторной остаются неизменными.

## Компоненты

- Prometheus: 6 целей, 10 правил (6 прежних + 4 CI/CD), хранение 7 дней.
- Grafana: Dashboard FishTrack Observability и отдельный Dashboard FishTrack CI/CD.
- Node Exporter: CPU, RAM, файловые системы и имя Linux-хоста. Используются PID/UTS хоста и корневая файловая система app-server.
- cAdvisor: метрики контейнеров Docker на app-server. Требуются стандартные `/var/lib/docker` и `/run/containerd/containerd.sock`; привилегированный контейнер допустим только на доверенном сервере.
- GitHub Actions exporter: чтение REST API каждые 120 секунд, scrape каждые 30 секунд. Никакого доступа на запись в GitHub, логов workflow или секретов.

## Подготовка VM

Убедиться, что подключение выполнено к нужному app-server, Docker Engine и Compose v2 работают, staging уже запущен. На VM:

```bash
hostname
hostname -I
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
curl -fsS http://127.0.0.1:8081/health
curl -fsS http://127.0.0.1:8081/version
```

Существующий `/opt/fishtrack-staging/compose.staging.yml` и `.env.staging` не перезаписываются. Если staging не работает, сначала восстановить его по существующей процедуре CD. Новый скрипт не строит образ и не изменяет БД. Для двух реплик должны быть доступны DNS-алиасы app1/app2 и `/metrics` внутри сети.

В GitHub создать fine-grained PAT для **Dadish76/fishtrack**, Repository permissions → Actions: Read-only (Metadata: Read-only автоматически). Установить срок действия. Если права на репозиторий не позволяют создать токен, его создает уполномоченный владелец. В чат и Git токен не передавать.

На VM скачать/обновить репозиторий с изменениями в отдельную папку (не `/opt/fishtrack-staging`), от обычного пользователя с доступом к Docker:

```bash
bash monitoring/start-app-server.sh
```

Скрипт проверяет hostname, локальный Docker socket, стандартные пути, проект и сеть, HTTP readiness и наличие метрик. Если hostname VM отличается, после проверки идентичности сервера разрешено `APP_SERVER_HOSTNAME=<фактическое-имя> bash monitoring/start-app-server.sh`. Метка `server=app-server` обозначает роль, фактическое имя проверяется через `node_uname_info`.

Пароль Grafana и GitHub PAT вводятся скрыто и сохраняются в `$HOME/.config/fishtrack-monitoring/` с ограниченными правами. Пароль Grafana доступен администраторам Docker, как и раньше. Если Grafana уже инициализирована, переменная не меняет сохраненный пароль. Для смены токена обновить файл `github-actions.token` безопасным редактором и пересоздать только exporter (из того же каталога мониторинга, с теми же переменными Compose) либо повторно запустить скрипт, который пересоздает exporter. Не выводить токен в терминал.

## Доступ с Windows через SSH

При работающем SSH-сервере использовать отдельное окно PowerShell:

```powershell
ssh -N -L 13000:127.0.0.1:3000 -L 19090:127.0.0.1:9090 -L 18081:127.0.0.1:8081 USER@VM_IP
```

Заменить USER и VM_IP реальными значениями. Порты 13000/19090/18081 выбраны, чтобы не конфликтовать с локальным Docker Desktop. Окно не закрывать во время демонстрации. Мониторинг не публикуется во внешнюю сеть.

- FishTrack: http://127.0.0.1:18081/health
- Grafana: http://127.0.0.1:13000/d/fishtrack-observability/fishtrack-observability
- CI/CD: http://127.0.0.1:13000/d/fishtrack-cicd/fishtrack-cicd
- Targets: http://127.0.0.1:19090/targets
- Alerts: http://127.0.0.1:19090/alerts

## Проверка источников

На app-server проверить `curl -fsS http://127.0.0.1:9090/-/ready` и `curl -fsS http://127.0.0.1:3000/api/health`. В Prometheus выполнить запросы:

```promql
up{server="app-server"}
node_uname_info{job="node"}
fishtrack_app_healthy{job="fishtrack"}
container_memory_working_set_bytes{job="cadvisor",container_label_com_docker_compose_project="fishtrack-staging"}
github_actions_api_up{job="github_actions"}
github_actions_stage_state{stage="deploy"} == 1
```

Ожидаются шесть целей UP, две готовые реплики, фактический nodename VM, метрики staging и API up=1. В Dashboard выбрать `fishtrack-staging`. Правила могут быть активны из-за фактического неуспешного запуска CI/CD; не считать их поломкой мониторинга. Доставка уведомлений Alertmanager не настроена.

## Метрики CI/CD: семантика

`github_actions_runs_window` — число запусков по состояниям в последних 30 запусках каждого workflow (все ветки), а не накопительный счетчик. `github_actions_success_ratio` — доля success среди завершенных запусков в этом окне (включая cancelled/skipped в знаменателе). `github_actions_latest_run_duration_seconds` — приближенная длительность последнего завершенного запуска, вычисляется из run_started_at и updated_at; для текущего незавершенного запуска отсутствует. `github_actions_stage_state` — состояние конкретного job последнего push develop; `stage_duration_seconds` — длительность job по started_at/completed_at. Skipped, missing, queued и failure не являются успехом CD. Это не DORA deployment frequency или MTTR и не доказательство доступности приложения; для приемки сопоставить job, SHA и `/version` на VM. Данные появятся после успешного опроса GitHub, не мгновенно. При ошибке API снимок удаляется, api_up=0, сохраняется время последнего успешного сбора.

## Обновление и безопасность

`bash monitoring/start-app-server.sh` повторно применяет конфигурацию, не удаляя тома. При изменении файлов Prometheus после обновления проверить загрузку правил; при необходимости отправить HUP контейнеру Prometheus после `promtool check config`. При изменении GitHub exporter пересоздать только его или перезапустить соответствующий контейнер. Не использовать `down -v`, глобальную очистку томов или копирование секретов в Git.

См. [Runbook](../docs/observability-runbook.md) и [исторические измерения](../docs/evidence/lab8/). Проверки CI: `.github/workflows/monitoring-ci.yml`.
