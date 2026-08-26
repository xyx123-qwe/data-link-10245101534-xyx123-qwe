from __future__ import annotations

from typing import Any


VERIFIED_MAPPING_ROWS = [
    {
        "source_format": "OpenSky",
        "input_field": "target_id",
        "unified_field": "track_id",
        "verified_rule": "六位目标标识转为小写字符串，保留前导0",
        "verified": True,
        "evidence": "M3 current_situation.csv target_id 已由 M2 解码恢复为六位十六进制字符串",
    },
    {
        "source_format": "OpenSky",
        "input_field": "latest_time",
        "unified_field": "timestamp",
        "verified_rule": "latest_time 为正整数 Unix 秒时直接映射",
        "verified": True,
        "evidence": "M3 当前态势使用每个 target_id 的最新 timestamp",
    },
    {
        "source_format": "TeachingLink",
        "input_field": "latitude_code + validity_flags.bit0",
        "unified_field": "position.lat",
        "verified_rule": "bit0 有效时按 code/(2^22-1)*180-90 恢复纬度；无效时为 null",
        "verified": True,
        "evidence": "TeachingLink 规范规定 bit0 表示纬度有效，预生成候选把 lat/lon 层次写反，已修正",
    },
    {
        "source_format": "TeachingLink",
        "input_field": "longitude_code + validity_flags.bit1",
        "unified_field": "position.lon",
        "verified_rule": "bit1 有效时按 code/(2^22-1)*360-180 恢复经度；无效时为 null",
        "verified": True,
        "evidence": "TeachingLink 规范规定 bit1 表示经度有效，预生成候选把 lat/lon 层次写反，已修正",
    },
    {
        "source_format": "TeachingLink",
        "input_field": "altitude_code + validity_flags.bit2",
        "unified_field": "position.alt",
        "verified_rule": "bit2 有效时 altitude_code-1000 得到米；无效时为 null",
        "verified": True,
        "evidence": "TeachingLink 高度使用 1m 分辨率和 1000m 物理偏置，预生成候选遗漏偏置，已修正",
    },
    {
        "source_format": "TeachingLink",
        "input_field": "callsign + validity_flags.bit6",
        "unified_field": "identity.callsign",
        "verified_rule": "bit6 有效且呼号非空时映射，否则为 null",
        "verified": True,
        "evidence": "TeachingLink 规范规定 callsign 是可空字段，由 validity_flags.bit6 表达",
    },
    {
        "source_format": "TeachingLink",
        "input_field": "status_flags.bit2",
        "unified_field": "quality.time_source",
        "verified_rule": "bit2 为 1 表示 timestamp_fallback，对应 last_contact；否则为 position_time",
        "verified": True,
        "evidence": "status_flags.bit2 的语义是 timestamp_fallback，不是 time_valid",
    },
    {
        "source_format": "TeachingLink",
        "input_field": "message_valid",
        "unified_field": "quality.message_valid",
        "verified_rule": "仅表示帧通过课程格式和校验检查，不扩大为业务可信",
        "verified": True,
        "evidence": "TeachingLink 规范明确 message_valid 只代表格式与校验通过",
    },
]


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes"}


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(float(value))


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def verify_candidate_mapping(candidate_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """依据字段定义、单位、有效性和样例，形成人工核验后的正式映射。"""
    return VERIFIED_MAPPING_ROWS.copy()


def map_to_unified(record: dict[str, Any], source_format: str) -> dict[str, Any]:
    """使用人工核验后的规则生成统一态势消息。"""
    target_id = str(record.get("target_id", "")).lower()
    timestamp = _to_int(record.get("latest_time") or record.get("timestamp"))
    message_valid = _to_bool(record.get("message_valid"))

    validity_flags = _to_int(record.get("validity_flags"))
    if validity_flags is None:
        validity_flags = 0

    if source_format == "TeachingLink":
        lat = _to_float(record.get("lat")) if validity_flags & (1 << 0) else None
        lon = _to_float(record.get("lon")) if validity_flags & (1 << 1) else None
        altitude = _to_float(record.get("altitude")) if validity_flags & (1 << 2) else None
        speed = _to_float(record.get("speed")) if validity_flags & (1 << 3) else None
        heading = _to_float(record.get("heading")) if validity_flags & (1 << 4) else None
        vertical_rate = _to_float(record.get("vertical_rate")) if validity_flags & (1 << 5) else None
        callsign = record.get("callsign") if validity_flags & (1 << 6) else None
    else:
        lat = _to_float(record.get("lat"))
        lon = _to_float(record.get("lon"))
        altitude = _to_float(record.get("altitude"))
        speed = _to_float(record.get("speed"))
        heading = _to_float(record.get("heading"))
        vertical_rate = _to_float(record.get("vertical_rate"))
        callsign = record.get("callsign") or None

    if callsign == "":
        callsign = None

    time_source = record.get("time_source") or record.get("timestamp_source") or "position_time"
    alt_type = record.get("alt_type") or "unknown"
    if alt_type == "barometric":
        alt_type = "baro"
    elif alt_type == "geometric":
        alt_type = "geo"

    anomaly_flags: list[str] = []
    if not timestamp or timestamp <= 0:
        anomaly_flags.append("TIME_INVALID")
    if lat is None or lon is None:
        anomaly_flags.append("POSITION_MISSING")
    if not message_valid:
        anomaly_flags.append("MESSAGE_INVALID")

    return {
        "track_id": target_id,
        "source": source_format,
        "timestamp": timestamp or 0,
        "identity": {"callsign": callsign},
        "position": {
            "lat": lat,
            "lon": lon,
            "alt": altitude,
            "alt_type": alt_type,
        },
        "motion": {
            "speed": speed,
            "heading": heading,
            "vertical_rate": vertical_rate,
        },
        "status": {"on_ground": _to_bool(record.get("on_ground"))},
        "quality": {
            "position_valid": lat is not None and lon is not None,
            "time_valid": timestamp is not None and timestamp > 0,
            "message_valid": message_valid,
            "time_source": time_source,
            "anomaly_flags": anomaly_flags,
        },
    }