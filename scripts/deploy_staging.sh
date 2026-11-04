#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

# Получаем конкретный тег образа
IMAGE_TAG="${1:?ERROR: Image tag is required}"

if [[ ! "$IMAGE_TAG" =~ ^sha-[0-9a-f]{40}$ ]] &&
   [[ ! "$IMAGE_TAG" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "ERROR: Invalid image tag: $IMAGE_TAG"
    exit 1
fi

export IMAGE_TAG

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

STAGING_DIR="/opt/fishtrack-staging"

cd "$STAGING_DIR"

# Дополнительная локальная защита от
# параллельных запусков скрипта
exec 9> .deploy.lock

if ! flock -n 9; then
    echo "ERROR: Another deployment is already running"
    exit 1
fi

# Проверяем необходимые файлы
test -f .env.staging || {
    echo "ERROR: .env.staging is missing"
    exit 1
}

test -f compose.staging.yml || {
    echo "ERROR: compose.staging.yml is missing"
    exit 1
}

# Команда для управления только staging
dc() {
    docker compose \
      -p fishtrack-staging \
      --env-file .env.staging \
      -f compose.staging.yml \
      "$@"
}

echo "===================================="
echo "FishTrack staging deployment"
echo "Image tag: $IMAGE_TAG"
echo "===================================="

# 1. Проверяем настройки
echo "[1/7] Checking configuration"
dc config -q

# 2. Получаем готовый образ из Registry
echo "[2/7] Pulling Docker image"
dc pull app1 app2

# 3. Проверяем готовность PostgreSQL
echo "[3/7] Starting staging database"
dc up -d --no-build --wait db

# 4. Применяем миграции
echo "[4/7] Applying Alembic migrations"
dc run --rm migrate

# 5. Обновляем контейнеры
echo "[5/7] Starting application and Nginx"
dc up -d --no-build --wait --wait-timeout 180 app1 app2 nginx

# 6. Базовые проверки доступности
echo "[6/7] Checking HTTP endpoints"

curl \
  --fail \
  --silent \
  --show-error \
  --retry 12 \
  --retry-delay 3 \
  --retry-connrefused \
  http://127.0.0.1:8081/docs \
  > /dev/null

curl \
  --fail \
  --silent \
  --show-error \
  --retry 6 \
  --retry-delay 2 \
  http://127.0.0.1:8081/openapi.json \
  > /dev/null

echo "HTTP checks passed"

# 7. Проверяем версию и пользовательский сценарий
echo "[7/7] Running FishTrack smoke tests"

python3 "${SCRIPT_DIR}/smoke_test.py" \
  --base-url "http://127.0.0.1:8081" \
  --expected-tag "$IMAGE_TAG"

echo "Smoke tests passed"

# Сохраняем предыдущий тег для ручного отката
PREVIOUS_TAG="$(sed -n 's/^IMAGE_TAG=//p' .env.staging | head -n 1)"

if [[ -n "$PREVIOUS_TAG" && "$PREVIOUS_TAG" != "$IMAGE_TAG" ]]; then
    printf '%s\n' "$PREVIOUS_TAG" > .previous-image-tag
fi

# Запоминаем развернутую версию между запусками
# без вывода секретов в журнал
TEMP_ENV="$(mktemp .env.staging.XXXXXX)"
trap 'rm -f "$TEMP_ENV"' EXIT

awk -v tag="$IMAGE_TAG" '
    /^IMAGE_TAG=/ {
        print "IMAGE_TAG=" tag
        found=1
        next
    }
    { print }
    END {
        if (!found) {
            print "IMAGE_TAG=" tag
        }
    }
' .env.staging > "$TEMP_ENV"

chmod 600 "$TEMP_ENV"
mv -f "$TEMP_ENV" .env.staging
trap - EXIT

echo "===================================="
echo "Staging updated: $IMAGE_TAG"
echo "Basic HTTP checks passed"
echo "Full smoke-test acceptance is pending"
echo "===================================="
