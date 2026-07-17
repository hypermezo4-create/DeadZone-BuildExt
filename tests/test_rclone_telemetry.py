from __future__ import annotations

from scripts.rclone_telemetry import TRANSFERRED_RE, _parse_eta, _parse_size


def test_parse_size_supports_decimal_and_binary_units() -> None:
    assert _parse_size("512 B") == 512
    assert _parse_size("1 B") == 1
    assert _parse_size("1.5 KiB") == 1536
    assert _parse_size("2 MiB") == 2 * 1024 * 1024
    assert _parse_size("1.25 KB") == 1250
    assert _parse_size("2.5 MB") == 2_500_000
    assert _parse_size("3.25 GB") == int(3.25 * 1000**3)


def test_parse_eta_supports_hours_minutes_and_seconds() -> None:
    assert _parse_eta("3s") == 3
    assert _parse_eta("4m") == 240
    assert _parse_eta("2m 05s") == 125
    assert _parse_eta("1h02m03s") == 3723
    assert _parse_eta("1h") == 3600
    assert _parse_eta("unknown") is None


def test_transferred_line_matches_realistic_rclone_output() -> None:
    line = "Transferred:   2.4 GiB / 5.8 GiB, 41%, 42.7 MiB/s, ETA 7m13s"
    match = TRANSFERRED_RE.search(line)
    assert match is not None
    assert _parse_size(match.group("processed")) == int(2.4 * 1024**3)
    assert _parse_size(match.group("total")) == int(5.8 * 1024**3)
    assert _parse_size(match.group("speed")) == int(42.7 * 1024**2)
    assert _parse_eta(match.group("eta")) == 433


def test_transferred_line_matches_metric_output_variants() -> None:
    line = "Transferred: 512 B / 1.5 KiB, 33%, 1.25 KB/s, ETA 4m"
    match = TRANSFERRED_RE.search(line)
    assert match is not None
    assert _parse_size(match.group("processed")) == 512
    assert _parse_size(match.group("total")) == 1536
    assert _parse_size(match.group("speed")) == 1250
    assert _parse_eta(match.group("eta")) == 240
