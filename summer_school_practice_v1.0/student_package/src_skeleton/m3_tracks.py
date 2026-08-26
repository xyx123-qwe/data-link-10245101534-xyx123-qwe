from __future__ import annotations

import sqlite3
from collections import defaultdict
from typing import Any

from student_package.src_skeleton.m2_protocol import FRAME_SIZE, decode_position_message


def decode_message_stream(data: bytes, frame_size: int = 41) -> list[dict[str, Any]]:
    """按固定帧长批量解码；记录并忽略不完整尾帧。"""
    records: list[dict[str, Any]] = []

    full_length = len(data) // frame_size * frame_size
    for offset in range(0, full_length, frame_size):
        frame = data[offset:offset + frame_size]
        record = decode_position_message(frame)
        record["frame_index"] = offset // frame_size + 1
        record["byte_offset"] = offset
        records.append(record)

    if len(data) % frame_size:
        records.append({
            "message_valid": False,
            "errors": ["LENGTH_ERROR"],
            "frame_index": len(data) // frame_size + 1,
            "byte_offset": full_length,
            "raw_length": len(data) - full_length,
        })

    return records


def save_records_to_sqlite(records: list[dict[str, Any]], db_path: str) -> None:
    """选做：保存接收记录，None必须写为NULL。"""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS received_states (
                target_id TEXT,
                timestamp INTEGER,
                message_seq INTEGER,
                callsign TEXT,
                lat REAL,
                lon REAL,
                altitude REAL,
                speed REAL,
                heading REAL,
                vertical_rate REAL,
                on_ground INTEGER,
                message_valid INTEGER
            )
            """
        )
        conn.execute("DELETE FROM received_states")
        for record in records:
            if not record.get("message_valid"):
                continue
            conn.execute(
                """
                INSERT INTO received_states (
                    target_id, timestamp, message_seq, callsign, lat, lon,
                    altitude, speed, heading, vertical_rate, on_ground, message_valid
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.get("target_id"),
                    record.get("timestamp"),
                    record.get("message_seq"),
                    record.get("callsign"),
                    record.get("lat"),
                    record.get("lon"),
                    record.get("altitude"),
                    record.get("speed"),
                    record.get("heading"),
                    record.get("vertical_rate"),
                    int(bool(record.get("on_ground"))),
                    int(bool(record.get("message_valid"))),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def _acceptable_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        record for record in records
        if record.get("message_valid") and record.get("target_id") and record.get("timestamp") is not None
    ]


def build_tracks(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """仅使用可接受记录，按target_id分组并按timestamp排序。"""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for record in _acceptable_records(records):
        grouped[record["target_id"]].append(record)

    track_rows: list[dict[str, Any]] = []
    for target_id in sorted(grouped):
        group = sorted(grouped[target_id], key=lambda row: (row["timestamp"], row.get("message_seq", 0)))
        for sequence_no, record in enumerate(group, start=1):
            track_rows.append({
                "target_id": target_id,
                "timestamp": record.get("timestamp"),
                "message_seq": record.get("message_seq"),
                "track_sequence_no": sequence_no,
                "lat": record.get("lat"),
                "lon": record.get("lon"),
                "altitude": record.get("altitude"),
                "speed": record.get("speed"),
                "heading": record.get("heading"),
            })

    return track_rows


def build_current_situation(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """每个目标保留时间最新的可接受记录；可选字段缺失仍可入选。"""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for record in _acceptable_records(records):
        grouped[record["target_id"]].append(record)

    rows: list[dict[str, Any]] = []
    for target_id in sorted(grouped):
        group = sorted(grouped[target_id], key=lambda row: (row["timestamp"], row.get("message_seq", 0)))
        latest = group[-1]
        rows.append({
            "target_id": target_id,
            "callsign": latest.get("callsign"),
            "latest_time": latest.get("timestamp"),
            "lat": latest.get("lat"),
            "lon": latest.get("lon"),
            "altitude": latest.get("altitude"),
            "speed": latest.get("speed"),
            "heading": latest.get("heading"),
            "vertical_rate": latest.get("vertical_rate"),
            "on_ground": latest.get("on_ground"),
            "track_length": len(group),
            "alt_type": latest.get("alt_type"),
            "time_source": latest.get("timestamp_source"),
            "message_valid": latest.get("message_valid"),
        })

    return rows