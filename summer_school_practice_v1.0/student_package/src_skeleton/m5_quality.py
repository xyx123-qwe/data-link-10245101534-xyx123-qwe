from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


BATCH_TIME = 1710000120
SEVERITY_RANK = {"NONE": 0, "MEDIUM": 1, "HIGH": 2}


def _is_missing(value: Any) -> bool:
    return value is None or value == ""


def _to_float(value: Any) -> float | None:
    if _is_missing(value):
        return None
    return float(value)


def _to_int(value: Any) -> int | None:
    if _is_missing(value):
        return None
    return int(float(value))


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def _alert(record: dict[str, Any], alert_type: str, severity: str, field: str, description: str, batch_time: int) -> dict[str, Any]:
    return {
        "alert_time": batch_time,
        "target_id": record.get("target_id", ""),
        "alert_type": alert_type,
        "severity": severity,
        "field": field,
        "description": description,
    }


def check_record(record: dict[str, Any], batch_time: int = BATCH_TIME) -> list[dict[str, Any]]:
    """检查位置缺失、时间延迟和航向越界。"""
    alerts: list[dict[str, Any]] = []

    lat = _to_float(record.get("lat"))
    lon = _to_float(record.get("lon"))
    timestamp = _to_int(record.get("latest_time") or record.get("timestamp"))
    heading = _to_float(record.get("heading"))

    if lat is None or lon is None:
        alerts.append(_alert(
            record,
            "POSITION_MISSING",
            "HIGH",
            "lat/lon",
            "lat or lon is missing",
            batch_time,
        ))

    if timestamp is None:
        alerts.append(_alert(
            record,
            "DATA_DELAYED",
            "MEDIUM",
            "timestamp",
            "timestamp is missing",
            batch_time,
        ))
    elif batch_time - timestamp > 60:
        alerts.append(_alert(
            record,
            "DATA_DELAYED",
            "MEDIUM",
            "timestamp",
            f"batch_time - timestamp = {batch_time - timestamp} seconds > 60",
            batch_time,
        ))

    if heading is not None and not (0 <= heading < 360):
        alerts.append(_alert(
            record,
            "HEADING_OUT_OF_RANGE",
            "MEDIUM",
            "heading",
            f"heading must satisfy 0 <= heading < 360, got {heading}",
            batch_time,
        ))

    return alerts


def check_duplicates(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """使用target_id+timestamp联合键检查重复。"""
    grouped: dict[tuple[str, int | None], list[dict[str, Any]]] = defaultdict(list)

    for record in records:
        key = (str(record.get("target_id", "")), _to_int(record.get("latest_time") or record.get("timestamp")))
        grouped[key].append(record)

    alerts: list[dict[str, Any]] = []
    for (target_id, timestamp), group in grouped.items():
        if target_id and timestamp is not None and len(group) > 1:
            for record in group:
                alerts.append(_alert(
                    record,
                    "DUPLICATE_RECORD",
                    "MEDIUM",
                    "target_id,timestamp",
                    f"duplicate target_id+timestamp key: {target_id}+{timestamp}",
                    BATCH_TIME,
                ))

    return alerts


def build_quality_situation(records: list[dict[str, Any]], alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按HIGH > MEDIUM > NONE合成质量态势。"""
    alerts_by_key: dict[tuple[str, int | None], list[dict[str, Any]]] = defaultdict(list)
    for alert in alerts:
        key_text = alert.get("description", "")
        alerts_by_key[(str(alert.get("target_id", "")), None)].append(alert)

    duplicate_keys = {
        alert["target_id"]
        for alert in alerts
        if alert.get("alert_type") == "DUPLICATE_RECORD"
    }

    rows: list[dict[str, Any]] = []
    for record in records:
        target_id = str(record.get("target_id", ""))
        timestamp = _to_int(record.get("latest_time") or record.get("timestamp"))

        record_alerts = [
            alert for alert in alerts
            if alert.get("target_id") == target_id
        ]

        alert_types = {alert["alert_type"] for alert in record_alerts}
        severities = [alert["severity"] for alert in record_alerts]
        anomaly_level = "NONE"
        if severities:
            anomaly_level = max(severities, key=lambda item: SEVERITY_RANK[item])

        position_valid = "POSITION_MISSING" not in alert_types
        delayed = "DATA_DELAYED" in alert_types
        duplicate_detected = target_id in duplicate_keys
        heading_valid = "HEADING_OUT_OF_RANGE" not in alert_types
        message_valid = _to_bool(record.get("message_valid"))

        if anomaly_level == "HIGH":
            display_status = "BLOCK"
        elif anomaly_level == "MEDIUM":
            display_status = "WARN"
        else:
            display_status = "OK"

        rows.append({
            "target_id": target_id,
            "timestamp": timestamp,
            "position_valid": position_valid,
            "delayed": delayed,
            "duplicate_detected": duplicate_detected,
            "heading_valid": heading_valid,
            "message_valid": message_valid,
            "anomaly_level": anomaly_level,
            "display_status": display_status,
        })

    return rows


def summarize_alerts(alerts: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(alert["alert_type"] for alert in alerts))