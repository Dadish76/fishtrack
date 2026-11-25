#!/usr/bin/env python3

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class SmokeTestError(RuntimeError):
    """Безопасная ошибка проверки релиза."""


def request_json(base_url, method, path, expected_statuses, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}

    if data is not None:
        headers["Content-Type"] = "application/json"

    token = os.getenv("SMOKE_BEARER_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    if path in {"/health", "/version", "/api/v1/boats"}:
        safe_path = path
    elif path.startswith("/api/v1/boats/"):
        safe_path = "/api/v1/boats/{boat_id}"
    else:
        safe_path = "unknown"

    request = Request(
        f"{base_url}{path}",
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urlopen(request, timeout=15) as response:
            status, content = response.status, response.read()

    except HTTPError as error:
        status, content = error.code, error.read()

    except URLError:
        # Не выводим подробности сетевого исключения.
        raise SmokeTestError(
            f"{method} {safe_path}: ошибка сетевого подключения"
        ) from None

    # Не выводим содержимое HTTP-ответа:
    # оно может содержать конфиденциальные данные.
    if status not in expected_statuses:
        raise SmokeTestError(f"{method} {safe_path}: неожиданный HTTP-код {status}")

    if status == 204 or not content:
        return status, None

    try:
        return status, json.loads(content)

    except (json.JSONDecodeError, UnicodeDecodeError):
        if status == 404:
            return status, None

        # Не выводим исходное содержимое некорректного JSON.
        raise SmokeTestError(f"{method} {safe_path}: некорректный JSON-ответ") from None


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--base-url", required=True)
    parser.add_argument("--expected-tag", required=True)
    parser.add_argument("--boat-payload-file", required=True)

    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    raw = Path(args.boat_payload_file).read_text(encoding="utf-8")

    # Проверяем наличие шаблона уникального идентификатора.
    if "{RUN_ID}" not in raw:
        raise SmokeTestError("Шаблон данных должен содержать {RUN_ID}")

    run_id = uuid.uuid4().hex[:12]

    boat = json.loads(raw.replace("{RUN_ID}", run_id))

    if not isinstance(boat, dict):
        raise SmokeTestError("Данные тестового катера должны быть JSON-объектом")

    required_fields = (
        "name",
        "registration_number",
        "capacity",
        "year_built",
    )

    for field in required_fields:
        if field not in boat:
            raise SmokeTestError(f"Отсутствует обязательное поле: {field}")

    # ============================================
    # 1. ПРОВЕРКА РАБОТОСПОСОБНОСТИ
    # ============================================

    print("[1/6] Проверка работоспособности", flush=True)

    _, health = request_json(
        base_url,
        "GET",
        "/health",
        (200,),
    )

    if not isinstance(health, dict) or health.get("status") != "healthy":
        raise SmokeTestError("Приложение не прошло проверку работоспособности")

    # ============================================
    # 2. ПРОВЕРКА ВЕРСИИ ПРИЛОЖЕНИЯ
    # ============================================

    print("[2/6] Проверка версии приложения", flush=True)

    _, release = request_json(
        base_url,
        "GET",
        "/version",
        (200,),
    )

    # Не выводим полное содержимое ответа сервера.
    if not isinstance(release, dict) or release.get("version") != args.expected_tag:
        raise SmokeTestError("Версия приложения не соответствует ожидаемой")

    boat_id = None
    deleted = False

    try:
        # ============================================
        # 3. СОЗДАНИЕ ТЕСТОВОГО КАТЕРА
        # ============================================

        print("[3/6] Создание тестового катера", flush=True)

        _, created = request_json(
            base_url,
            "POST",
            "/api/v1/boats",
            (200, 201),
            boat,
        )

        if not isinstance(created, dict):
            raise SmokeTestError("Ответ POST не содержит объект катера")

        boat_id = created.get(
            "id",
            created.get("boat_id"),
        )

        if boat_id is None:
            raise SmokeTestError("Ответ POST не содержит идентификатор катера")

        item_path = f"/api/v1/boats/{quote(str(boat_id), safe='')}"

        # ============================================
        # 4. ЧТЕНИЕ И СРАВНЕНИЕ ДАННЫХ
        # ============================================

        print(
            "[4/6] Чтение и сравнение сохраненных данных",
            flush=True,
        )

        _, persisted = request_json(
            base_url,
            "GET",
            item_path,
            (200,),
        )

        if not isinstance(persisted, dict):
            raise SmokeTestError("Ответ GET не содержит объект катера")

        # Проверяем значения полей, не выводя
        # их фактическое содержимое в журналы.
        for field in required_fields:
            if persisted.get(field) != boat[field]:
                raise SmokeTestError(
                    f"Значение поля {field} " "не соответствует ожидаемому"
                )

        # ============================================
        # 5. УДАЛЕНИЕ ТЕСТОВОГО КАТЕРА
        # ============================================

        print("[5/6] Удаление тестового катера", flush=True)

        request_json(
            base_url,
            "DELETE",
            item_path,
            (200, 204),
        )

        deleted = True

        # ============================================
        # 6. ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ
        # ============================================

        print("[6/6] Подтверждение удаления", flush=True)

        request_json(
            base_url,
            "GET",
            item_path,
            (404,),
        )

    finally:
        # Удаляем только запись, идентификатор которой
        # был получен при создании тестового катера.
        # При ошибке выполняем дополнительную очистку.
        if boat_id is not None and not deleted:
            try:
                item_path = f"/api/v1/boats/{quote(str(boat_id), safe='')}"

                request_json(
                    base_url,
                    "DELETE",
                    item_path,
                    (200, 204, 404),
                )

                print(
                    "Очистка: тестовый катер удален",
                    flush=True,
                )

            except Exception as error:
                # Записываем только тип исключения,
                # не раскрывая его содержимое.
                print(
                    "WARNING: Ошибка очистки тестовых данных: "
                    f"{type(error).__name__}",
                    file=sys.stderr,
                )

    print(
        "PASS: FishTrack create → read → compare → delete → 404",
        flush=True,
    )


if __name__ == "__main__":
    try:
        main()

    except SmokeTestError as error:
        # Выводим только собственные безопасные сообщения.
        print(
            f"SMOKE FAILED: {error}",
            file=sys.stderr,
        )

        sys.exit(1)

    except Exception as error:
        # Не выводим подробности непредвиденных исключений,
        # поскольку они могут содержать секреты.
        print(
            f"SMOKE FAILED: {type(error).__name__}",
            file=sys.stderr,
        )

        sys.exit(1)
