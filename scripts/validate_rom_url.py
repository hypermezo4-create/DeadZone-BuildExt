#!/usr/bin/env python3
"""Fail-closed validation for ROM URLs before private engine checkout."""

from __future__ import annotations

import argparse
import ipaddress
import socket
from urllib.parse import urlsplit


class UrlValidationError(ValueError):
    pass


def _public_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise UrlValidationError("ROM URL host resolved to an invalid IP address") from exc
    return address.is_global


def validate_url(raw_url: str, *, resolver=socket.getaddrinfo) -> None:
    if not raw_url:
        raise UrlValidationError("ROM URL is empty")
    if raw_url != raw_url.strip() or any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in raw_url):
        raise UrlValidationError("ROM URL contains whitespace or control characters")

    try:
        parsed = urlsplit(raw_url)
        port = parsed.port
    except ValueError as exc:
        raise UrlValidationError("ROM URL has a malformed host or port") from exc

    if parsed.scheme.lower() != "https":
        raise UrlValidationError("ROM URL must use HTTPS")
    if not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise UrlValidationError("ROM URL must have a host and must not contain credentials")
    if port not in (None, 443):
        raise UrlValidationError("ROM URL must use the default HTTPS port")

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise UrlValidationError("ROM URL host is not public")
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = None
    if literal is not None:
        if not literal.is_global:
            raise UrlValidationError("ROM URL IP address is not public")
        return

    try:
        answers = resolver(hostname, port or 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise UrlValidationError("ROM URL host cannot be resolved") from exc
    addresses = {answer[4][0].split("%", 1)[0] for answer in answers if answer and len(answer) > 4}
    if not addresses or any(not _public_address(address) for address in addresses):
        raise UrlValidationError("ROM URL host does not resolve exclusively to public addresses")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    args = parser.parse_args(argv)
    try:
        validate_url(args.url)
    except UrlValidationError as exc:
        parser.error(str(exc))
    print("ROM URL passed public HTTPS validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
