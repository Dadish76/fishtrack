#!/usr/bin/env python3

import argparse
import json
from urllib.request import urlopen


def get_json(url):
    with urlopen(url, timeout=10) as response:
        if response.status != 200:
            raise RuntimeError(
                f"Unexpected status: {response.status}"
            )
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--expected-tag", required=True)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")

    print("[1/2] Checking OpenAPI")
    schema = get_json(f"{base}/openapi.json")
    assert schema.get("paths"), "OpenAPI paths missing"

    print("[2/2] Checking deployed version")
    result = get_json(f"{base}/version")

    actual = result.get("version")

    assert actual == args.expected_tag, (
        f"Expected {args.expected_tag}, got {actual}"
    )

    print("Basic smoke checks passed")


if __name__ == "__main__":
    main()
