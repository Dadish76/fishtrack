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


def request_json(base_url, method, path, expected_statuses, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"

    # Optional, staging-only API token; never commit the token.
    token = os.getenv("SMOKE_BEARER_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(
        f"{base_url}{path}", data=data, headers=headers, method=method
    )
    try:
        with urlopen(request, timeout=15) as response:
            status, content = response.status, response.read()
    except HTTPError as error:
        status, content = error.code, error.read()
    except URLError as error:
        raise RuntimeError(f"{method} {path}: network failure: {error.reason}") from error

    if status not in expected_statuses:
        excerpt = content.decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"{method} {path}: HTTP {status}; response={excerpt!r}")

    if status == 204 or not content:
        return status, None
    try:
        return status, json.loads(content)
    except json.JSONDecodeError as error:
        if status == 404:
            return status, None
        raise RuntimeError(f"{method} {path}: invalid JSON response") from error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--expected-tag", required=True)
    parser.add_argument("--boat-payload-file", required=True)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    raw = Path(args.boat_payload_file).read_text(encoding="utf-8")
    if "{RUN_ID}" not in raw:
        raise ValueError("Payload must contain {RUN_ID} for a unique test boat")
    run_id = uuid.uuid4().hex[:12]
    boat = json.loads(raw.replace("{RUN_ID}", run_id))
    if not isinstance(boat, dict):
        raise ValueError("Boat payload must be a JSON object")
    for field in ("name", "registration_number", "capacity", "year_built"):
        if field not in boat:
            raise ValueError(f"Boat payload lacks {field!r}")

    print("[1/6] Health", flush=True)
    _, health = request_json(base_url, "GET", "/health", (200,))
    if not isinstance(health, dict) or health.get("status") != "healthy":
        raise AssertionError(f"Unexpected health response: {health!r}")

    print("[2/6] Version", flush=True)
    _, release = request_json(base_url, "GET", "/version", (200,))
    if not isinstance(release, dict) or release.get("version") != args.expected_tag:
        raise AssertionError(
            f"Expected version {args.expected_tag!r}, got {release!r}"
        )

    boat_id = None
    deleted = False
    try:
        print("[3/6] Create test boat", flush=True)
        _, created = request_json(
            base_url, "POST", "/api/v1/boats", (200, 201), boat
        )
        if not isinstance(created, dict):
            raise AssertionError(f"POST did not return a boat object: {created!r}")
        boat_id = created.get("id", created.get("boat_id"))
        if boat_id is None:
            raise AssertionError(f"POST response has no id or boat_id: {created!r}")
        item_path = f"/api/v1/boats/{quote(str(boat_id), safe='')}"

        print("[4/6] Read and compare persisted boat", flush=True)
        _, persisted = request_json(base_url, "GET", item_path, (200,))
        if not isinstance(persisted, dict):
            raise AssertionError(f"GET did not return a boat object: {persisted!r}")
        for field in ("name", "registration_number", "capacity", "year_built"):
            if persisted.get(field) != boat[field]:
                raise AssertionError(
                    f"{field}: expected {boat[field]!r}, "
                    f"got {persisted.get(field)!r}"
                )

        print("[5/6] Delete test boat", flush=True)
        request_json(base_url, "DELETE", item_path, (200, 204))
        deleted = True

        print("[6/6] Confirm deletion", flush=True)
        request_json(base_url, "GET", item_path, (404,))
    finally:
        # Never delete real data: only the record ID returned by our own POST.
        if boat_id is not None and not deleted:
            try:
                item_path = f"/api/v1/boats/{quote(str(boat_id), safe='')}"
                request_json(base_url, "DELETE", item_path, (200, 204, 404))
                print("Cleanup: test boat removed", flush=True)
            except Exception as error:
                print(f"WARNING: cleanup failed: {error}", file=sys.stderr)

    print("PASS: FishTrack create → read → compare → delete → 404", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, ValueError, OSError, RuntimeError) as error:
        print(f"SMOKE FAILED: {error}", file=sys.stderr)
        sys.exit(1)
