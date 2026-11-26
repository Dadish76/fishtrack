#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

# Запускать от обычного пользователя с доступом к Docker НА app-server.
[[ "$(uname -s)" == Linux ]] || { echo 'ERROR: Требуется Linux app-server'; exit 1; }
[[ "$(id -u)" != 0 ]] || { echo 'ERROR: Запустите от пользователя VM с доступом к Docker, не от root'; exit 1; }
expected_host="${APP_SERVER_HOSTNAME:-app-server}"
[[ "$(hostname -s)" == "$expected_host" ]] || { echo 'ERROR: hostname не соответствует app-server; проверьте VM'; exit 1; }
unset DOCKER_HOST DOCKER_CONTEXT
# Явно выбираем локальный демон Linux, а не удаленный Docker context.
docker_local() { docker --host unix:///var/run/docker.sock "$@"; }
[[ "$(docker_local info --format '{{.OperatingSystem}}')" != *'Docker Desktop'* ]] || { echo 'ERROR: Docker Desktop запрещен'; exit 1; }
[[ "$(docker_local info --format '{{.DockerRootDir}}')" == /var/lib/docker ]] || { echo 'ERROR: Нестандартный DockerRootDir; адаптируйте cAdvisor'; exit 1; }
[[ -S /run/containerd/containerd.sock ]] || { echo 'ERROR: Не найден сокет /run/containerd/containerd.sock'; exit 1; }
command -v python3 >/dev/null
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

# Не создаем и не изменяем приложение или БД: используем уже работающий staging.
project=fishtrack-staging
for service in app1 app2 db nginx; do
    mapfile -t containers < <(docker_local ps --filter "label=com.docker.compose.project=$project" --filter "label=com.docker.compose.service=$service" --format '{{.ID}}')
    [[ "${#containers[@]}" == 1 ]] || { echo "ERROR: Требуется один работающий $project/$service"; exit 1; }
    if [[ "$service" == app1 ]]; then app1="${containers[0]}"; fi
    if [[ "$service" == app2 ]]; then app2="${containers[0]}"; fi
done
# Выбираем единственную общую сеть, где есть DNS-алиасы app1 и app2.
network1="$(docker_local inspect --format '{{json .NetworkSettings.Networks}}' "$app1")"
network2="$(docker_local inspect --format '{{json .NetworkSettings.Networks}}' "$app2")"
FISHTRACK_NETWORK="$(python3 - "$network1" "$network2" <<'PY'
import json, sys
left, right = (json.loads(s) for s in sys.argv[1:])
common = [n for n in left.keys() & right.keys()
          if 'app1' in (left[n].get('Aliases') or [])
          and 'app2' in (right[n].get('Aliases') or [])]
if len(common) != 1:
    sys.exit('ERROR: Не удалось однозначно определить сеть приложения')
print(common[0])
PY
)"
export FISHTRACK_NETWORK
printf 'Server: %s\nApplication network: %s\n' "$(hostname -s)" "$FISHTRACK_NETWORK"
curl -fsS --max-time 10 http://127.0.0.1:8081/health >/dev/null
for container in "$app1" "$app2"; do
    docker_local exec "$container" python -c 'import urllib.request; r=urllib.request.urlopen("http://127.0.0.1:8000/metrics", timeout=5); assert b"fishtrack_app_healthy" in r.read()'
done

# Секреты хранятся вне Git, доступны только владельцу и администраторам Docker.
secret_dir="$HOME/.config/fishtrack-monitoring"
mkdir -p "$secret_dir"
chmod 700 "$secret_dir"
export GITHUB_TOKEN_PATH="$secret_dir/github-actions.token"
export GITHUB_EXPORTER_UID="$(id -u)" GITHUB_EXPORTER_GID="$(id -g)"
if [[ ! -s "$GITHUB_TOKEN_PATH" ]]; then
    read -rsp 'GitHub fine-grained PAT (Actions: Read): ' token; echo
    [[ -n "$token" ]] || { echo 'ERROR: Пустой токен'; exit 1; }
    printf '%s' "$token" > "$GITHUB_TOKEN_PATH"
    unset token
fi
chmod 600 "$GITHUB_TOKEN_PATH"
[[ -O "$GITHUB_TOKEN_PATH" ]] || { echo 'ERROR: Токен должен принадлежать текущему пользователю'; exit 1; }
password_file="$secret_dir/grafana-password"
if [[ ! -s "$password_file" ]]; then
    read -rsp 'Пароль администратора Grafana (минимум 12 символов): ' password; echo
    [[ "${#password}" -ge 12 ]] || { echo 'ERROR: Слишком короткий пароль'; exit 1; }
    printf '%s' "$password" > "$password_file"
    unset password
fi
chmod 600 "$password_file"
GRAFANA_ADMIN_PASSWORD="$(cat "$password_file")"
export GRAFANA_ADMIN_PASSWORD
mon() { docker_local compose -p fishtrack-server-monitoring -f compose.yml "$@"; }
mon config --quiet
mon run --rm --no-deps --entrypoint /bin/promtool prometheus check config /etc/prometheus/prometheus.yml
mon up -d
# Перечитываем конфигурацию даже если Compose не пересоздал контейнер.
mon exec -T prometheus /bin/promtool check config /etc/prometheus/prometheus.yml
mon kill -s HUP prometheus
# Применяем новый код и новый inode файла токена при обновлении.
mon up -d --no-deps --force-recreate github-actions
mon ps
printf '\nПроверка после запуска: curl -fsS http://127.0.0.1:9090/-/ready\n'
printf 'Grafana и Prometheus доступны через SSH-туннель; токены не выводятся.\n'
