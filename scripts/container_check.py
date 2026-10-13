
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parent.parent
URL = "http://127.0.0.1:8080/login"


def run(*args):
    result = subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(args)}\n"
            f"{result.stderr[-1500:]}"
        )

    return result.stdout.strip()


def compose(*args):
    return run(
        "docker",
        "compose",
        "--env-file",
        ".env.container",
        *args,
    )


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def pinned_image(image):
    if "@sha256:" in image:
        return True

    last_part = image.rsplit("/", 1)[-1]
    return ":" in last_part and not last_part.endswith(":latest")


def check_configuration():
    print("[1/7] Checking Compose configuration")

    config = json.loads(
        compose("config", "--format", "json")
    )
    services = config["services"]

    required = (
        "db",
        "migrate",
        "init-admin",
        "app1",
        "app2",
        "nginx",
    )

    for name in required:
        require(
            name in services,
            f"Required service is missing: {name}",
        )

    for name, service in services.items():
        image = service.get("image", "")
        require(
            image and pinned_image(image),
            f"{name}: image must have a fixed tag or digest",
        )

        health = service.get("healthcheck", {})
        require(
            not health.get("disable", False)
            and health.get("test") != ["NONE"],
            f"{name}: healthcheck is disabled",
        )

    for name in ("db", "app1", "app2", "migrate", "init-admin", "db-restore"):
        if name in services:
            require(
                not services[name].get("ports"),
                f"{name}: published ports are forbidden",
            )

    nginx_ports = services["nginx"].get("ports", [])
    require(
        len(nginx_ports) == 1
        and str(nginx_ports[0].get("published")) == "8080"
        and str(nginx_ports[0].get("target")) == "80",
        "Nginx must publish only 8080:80",
    )

    for name in ("db", "app1", "app2"):
        health = services[name].get("healthcheck", {})
        require(
            bool(health.get("test"))
            and health.get("test") != ["NONE"],
            f"{name}: healthcheck is missing",
        )

    for name in ("db", "app1", "app2", "nginx"):
        service = services[name]
        require(
            service.get("cpus") is not None
            and service.get("mem_limit") is not None,
            f"{name}: resource limits are missing",
        )

    dependencies = services["init-admin"].get("depends_on", {})
    require(
        dependencies.get("migrate", {}).get("condition")
        == "service_completed_successfully",
        "init-admin must wait for migrations",
    )

    for name in ("app1", "app2"):
        dependencies = services[name].get("depends_on", {})
        require(
            dependencies.get("init-admin", {}).get("condition")
            == "service_completed_successfully",
            f"{name} must wait for init-admin",
        )

    dockerfile = (ROOT / "Dockerfile").read_text(
        encoding="utf-8"
    )

    for line in dockerfile.splitlines():
        if line.strip().upper().startswith("FROM "):
            image = line.split()[1]
            require(
                pinned_image(image),
                f"Dockerfile has unpinned image: {image}",
            )

    ignored = (ROOT / ".dockerignore").read_text(
        encoding="utf-8"
    )

    require(
        ".env" in ignored,
        ".dockerignore must exclude environment files",
    )

    tracked = run(
        "git",
        "ls-files",
        "--",
        ".env.container",
    )

    require(
        not tracked,
        ".env.container must not be tracked by Git",
    )

    print("PASS: configuration")


def check_image_security():
    print("[2/7] Checking application image security")

    image_env = json.loads(
        run(
            "docker",
            "image",
            "inspect",
            "fishtrack:0.4.0",
            "--format",
            "{{json .Config.Env}}",
        )
    )

    forbidden = (
        "DATABASE_URL=",
        "SECRET_KEY=",
        "POSTGRES_PASSWORD=",
        "ADMIN_PASSWORD=",
    )

    for variable in image_env:
        require(
            not variable.startswith(forbidden),
            "Secret configuration is embedded in the image",
        )

    for service in ("app1", "app2"):
        uid = compose("exec", "-T", service, "id", "-u")
        require(
            uid != "0",
            f"{service} is running as root",
        )

    print("PASS: non-root, no secrets in image ENV")


def wait_healthy(service, timeout=90):
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        container_id = compose("ps", "-q", service)

        if container_id:
            status = run(
                "docker",
                "inspect",
                "--format",
                "{{.State.Health.Status}}",
                container_id,
            )

            if status == "healthy":
                return

        time.sleep(2)

    raise RuntimeError(
        f"{service} did not become healthy"
    )


def check_job_exit(service):
    container_id = compose("ps", "-a", "-q", service)

    require(
        bool(container_id),
        f"{service}: container not found",
    )

    exit_code = run(
        "docker",
        "inspect",
        "--format",
        "{{.State.ExitCode}}",
        container_id,
    )

    require(
        exit_code == "0",
        f"{service} failed with exit code {exit_code}",
    )


def check_startup():
    print("[3/7] Building and starting containers")

    compose("up", "-d", "--build")

    for service in ("db", "app1", "app2"):
        wait_healthy(service)

    print("PASS: containers are healthy")


def check_migrations():
    print("[4/7] Checking migrations and initialization")

    check_job_exit("migrate")
    check_job_exit("init-admin")

    print("PASS: one-shot jobs exited with code 0")


def http_request():
    with urlopen(URL, timeout=6) as response:
        require(
            response.status == 200,
            f"Unexpected HTTP status: {response.status}",
        )

        return response.headers.get("X-Instance-ID", "")


def check_http():
    print("[5/7] Checking HTTP through Nginx")

    instance = http_request()

    require(
        instance in ("app1", "app2"),
        f"Invalid X-Instance-ID: {instance}",
    )

    print("PASS: HTTP 200 through Nginx")


def check_balancing():
    print("[6/7] Checking load balancing")

    instances = set()

    for _ in range(20):
        instances.add(http_request())

    require(
        instances == {"app1", "app2"},
        f"Both instances were not observed: {instances}",
    )

    print("PASS: both instances handled requests")


def check_failover():
    print("[7/7] Checking Nginx failover")

    stopped = False

    try:
        compose("stop", "app1")
        stopped = True

        time.sleep(2)

        for _ in range(5):
            instance = http_request()
            require(
                instance == "app2",
                "Failover did not route to app2",
            )

    finally:
        if stopped:
            compose("start", "app1")
            wait_healthy("app1")

    print("PASS: failover, app1 restored")


def main():
    check_configuration()
    check_startup()
    check_image_security()
    check_migrations()
    check_http()
    check_balancing()
    check_failover()

    print()
    print("ALL CONTAINER CHECKS PASSED")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"CONTAINER CHECK FAILED: {exc}")
        sys.exit(1)
