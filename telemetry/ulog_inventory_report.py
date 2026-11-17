"""Render a ULog inventory report for the command line."""


def _field(value: object) -> str:
    return "-" if value is None else str(value)


def render(report: dict[str, object]) -> str:
    """One screen: file status, one row per subscription, then the views."""
    file = report["file"]
    assert isinstance(file, dict)
    head = f"{file['name']}  {file['bytes']} B  status {report['status']}"
    if report.get("reason"):
        head += f" ({report['reason']} at byte {_field(report.get('offset'))})"
    lines = [head]
    if "subscriptions" not in report:
        return "\n".join(lines)
    dropouts = report["dropouts"]
    assert isinstance(dropouts, dict)
    lines.append(
        f"ULog v{_field(report['ulog_version'])}  firmware "
        f"{_field(report['firmware'])}  hardware {_field(report['hardware'])}  "
        f"frames {report['frames']}  dropout markers {dropouts['markers']} "
        f"({dropouts['duration_ms']} ms)  features "
        f"{','.join(report['features']) or '-'}"  # type: ignore[arg-type]
    )
    lines.append("")
    lines.append(
        f"{'topic':<40} {'inst':>4} {'samples':>9} {'span_s':>9} {'fields':>6}  mapping"
    )
    rows = report["subscriptions"]
    assert isinstance(rows, list)
    for row in rows:
        first, last = row["first_us"], row["last_us"]
        span = "-" if first is None or last is None else f"{(last - first) / 1e6:.1f}"
        lines.append(
            f"{row['topic']:<40} {row['instance']:>4} {row['samples']:>9} "
            f"{span:>9} {len(row['fields']):>6}  {row['mapping']}"
        )
    lines.append("")
    views = report["views"]
    assert isinstance(views, dict)
    for name, view in views.items():
        parts = ", ".join(
            f"{t['topic']} {t['state']} ({_field(t['samples'])} samples)"
            for t in view["topics"]
        )
        lines.append(f"view {name:<8} {view['state']:<22} {parts}")
    replay = report["replay"]
    assert isinstance(replay, dict)
    lines.append(
        f"replay   {replay['status']}  profile {_field(replay['profile'])}"
        + (f"  reasons {', '.join(replay['reasons'])}" if replay["reasons"] else "")
    )
    return "\n".join(lines)
