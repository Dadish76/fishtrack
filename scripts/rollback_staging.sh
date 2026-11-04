#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

# Ручной откат FishTrack staging.
# Использование:
# bash scripts/rollback_staging.sh sha-<40 символов SHA>

GOOD_TAG="${1:?ERROR: Specify a known-good image tag}"

# Допускаем только SHA-теги или версии вида 0.4.0.
if [[ ! "$GOOD_TAG" =~ ^sha-[0-9a-f]{40}$ ]] &&
   [[ ! "$GOOD_TAG" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "ERROR: Invalid image tag: $GOOD_TAG"
    exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

DEPLOY_SCRIPT="${SCRIPT_DIR}/deploy_staging.sh"
STAGING_DIR="/opt/fishtrack-staging"
REGISTRY_IMAGE="localhost:5000/fishtrack:${GOOD_TAG}"

if [[ ! -f "$DEPLOY_SCRIPT" ]]; then
    echo "ERROR: deploy_staging.sh is missing"
    exit 1
fi

if [[ ! -f "${STAGING_DIR}/.env.staging" ]]; then
    echo "ERROR: staging environment is missing"
    exit 1
fi

echo "========================================"
echo "FishTrack manual rollback"
echo "Target image: ${REGISTRY_IMAGE}"
echo "========================================"

echo "[1/4] Checking Docker Registry"
curl --fail --silent --show-error \
    http://127.0.0.1:5000/v2/ > /dev/null

echo "[2/4] Deploying selected known-good tag"

# Используем тот же проверенный механизм,
# что и автоматический CD.
# Он уже содержит flock, pull, migrations
# и post-deploy smoke tests.
bash "$DEPLOY_SCRIPT" "$GOOD_TAG"

echo "[3/4] Checking running container images"

for SERVICE in app1 app2; do
    CONTAINER="fishtrack-staging-${SERVICE}-1"

    ACTUAL_IMAGE="$(
        docker inspect "$CONTAINER" \
            --format '{{.Config.Image}}'
    )"

    if [[ "$ACTUAL_IMAGE" != "$REGISTRY_IMAGE" ]]; then
        echo "ERROR: ${SERVICE} uses ${ACTUAL_IMAGE}"
        exit 1
    fi

    echo "${SERVICE}: ${ACTUAL_IMAGE}"
done

echo "[4/4] Checking recorded staging version"

RECORDED_TAG="$(
    sed -n 's/^IMAGE_TAG=//p' \
        "${STAGING_DIR}/.env.staging"
)"

if [[ "$RECORDED_TAG" != "$GOOD_TAG" ]]; then
    echo "ERROR: Recorded tag does not match rollback target"
    exit 1
fi

echo "========================================"
echo "ROLLBACK SUCCESSFUL"
echo "Restored image: ${REGISTRY_IMAGE}"
echo "Post-deploy checks: passed"
echo "========================================"
