from __future__ import annotations

import socket

import pytest

from scripts.validate_rom_url import UrlValidationError, validate_url


def _resolver(address: str):
    return lambda *_args, **_kwargs: [(socket.AF_INET6 if ":" in address else socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))]


def test_accepts_https_and_signed_query() -> None:
    validate_url("https://downloads.example.test/rom.zip?sig=a%2Bb&expires=9", resolver=_resolver("93.184.216.34"))


@pytest.mark.parametrize(
    "value",
    [
        "",
        "http://example.test/rom.zip",
        "https://example.test/a b.zip",
        "https://example.test/a\n.zip",
        "https://user:pass@example.test/rom.zip",
        "https://127.0.0.1/rom.zip",
        "https://10.0.0.1/rom.zip",
        "https://[::1]/rom.zip",
        "https://example.test:8443/rom.zip",
    ],
)
def test_rejects_unsafe_urls(value: str) -> None:
    with pytest.raises(UrlValidationError):
        validate_url(value, resolver=_resolver("93.184.216.34"))


def test_rejects_hostname_resolving_private() -> None:
    with pytest.raises(UrlValidationError):
        validate_url("https://downloads.example.test/rom.zip", resolver=_resolver("192.168.1.4"))
