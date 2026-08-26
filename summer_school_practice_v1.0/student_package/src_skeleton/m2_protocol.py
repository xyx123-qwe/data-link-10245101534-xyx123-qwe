from __future__ import annotations

import math
import re
from typing import Any


FRAME_SIZE = 41


def _is_missing(value: Any) -> bool:
    return value is None


def _require_number(value: Any, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number or None")
    if not math.isfinite(float(value)):
        raise ValueError(f"{field} must be finite")
    return float(value)


def _check_range(value: float | None, field: str, low: float, high: float, high_inclusive: bool = True) -> float | None:
    if value is None:
        return None
    ok = low <= value <= high if high_inclusive else low <= value < high
    if not ok:
        end = "<=" if high_inclusive else "<"
        raise ValueError(f"{field} out of range: expected {low} <= value {end} {high}, got {value}")
    return value


def parse_state_vector(vector: list[Any]) -> dict[str, Any]:
    """将OpenSky状态向量转换为发送方内部结构化记录。"""
    if len(vector) < 17:
        raise ValueError(f"state vector too short: {len(vector)}")

    icao24 = vector[0]
    if not isinstance(icao24, str) or not re.fullmatch(r"[0-9a-fA-F]{6}", icao24):
        raise ValueError(f"target_id must be a 6-digit hex string: {icao24!r}")
    target_id = icao24.lower()

    raw_callsign = vector[1]
    callsign = None
    if raw_callsign is not None:
        if not isinstance(raw_callsign, str):
            raise ValueError("callsign must be a string or None")
        callsign = raw_callsign.strip()
        if callsign:
            try:
                callsign.encode("ascii")
            except UnicodeEncodeError as exc:
                raise ValueError(f"callsign must be ASCII: {callsign!r}") from exc
            if len(callsign) > 8:
                raise ValueError(f"callsign too long: {callsign!r}")
        else:
            callsign = None

    time_position = vector[3]
    last_contact = vector[4]
    if time_position is not None:
        timestamp = int(time_position)
        timestamp_source = "position_time"
        timestamp_fallback = False
    elif last_contact is not None:
        timestamp = int(last_contact)
        timestamp_source = "last_contact"
        timestamp_fallback = True
    else:
        raise ValueError("timestamp missing: both time_position and last_contact are None")

    lon = _check_range(_require_number(vector[5], "longitude"), "longitude", -180.0, 180.0)
    lat = _check_range(_require_number(vector[6], "latitude"), "latitude", -90.0, 90.0)

    baro_altitude = _require_number(vector[7], "baro_altitude")
    geo_altitude = _require_number(vector[13], "geo_altitude")
    if baro_altitude is not None:
        altitude = baro_altitude
        alt_type = "baro"
        altitude_is_geometric = False
    elif geo_altitude is not None:
        altitude = geo_altitude
        alt_type = "geo"
        altitude_is_geometric = True
    else:
        altitude = None
        alt_type = "unknown"
        altitude_is_geometric = False

    if altitude is not None:
        _check_range(altitude, "altitude", -1000.0, 64535.0)

    on_ground = vector[8]
    if not isinstance(on_ground, bool):
        raise ValueError(f"on_ground must be bool: {on_ground!r}")

    speed = _check_range(_require_number(vector[9], "velocity"), "velocity", 0.0, 6553.5)
    heading = _check_range(_require_number(vector[10], "true_track"), "true_track", 0.0, 360.0, high_inclusive=False)
    vertical_rate = _check_range(_require_number(vector[11], "vertical_rate"), "vertical_rate", -327.68, 327.67)

    return {
        "target_id": target_id,
        "callsign": callsign,
        "timestamp": timestamp,
        "timestamp_source": timestamp_source,
        "timestamp_fallback": timestamp_fallback,
        "lat": lat,
        "lon": lon,
        "altitude": altitude,
        "alt_type": alt_type,
        "altitude_is_geometric": altitude_is_geometric,
        "on_ground": on_ground,
        "speed": speed,
        "heading": heading,
        "vertical_rate": vertical_rate,
    }


def calculate_checksum(data_without_checksum: bytes) -> int:
    """计算前39字节无符号字节值之和模65536。"""
    if len(data_without_checksum) != 39:
        raise ValueError(f"checksum input must be 39 bytes, got {len(data_without_checksum)}")
    return sum(data_without_checksum) % 65536

def _q(value: float) -> int:
    return math.floor(value + 0.5)


def encode_position_message(record: dict[str, Any], message_seq: int) -> bytes:
    """按41字节TeachingLink格式封装一条位置状态消息。"""
    frame = bytearray(FRAME_SIZE)

    frame[0:2] = (0x4453).to_bytes(2, "big")
    frame[2] = 1
    frame[3] = 1
    frame[4:6] = FRAME_SIZE.to_bytes(2, "big")
    frame[6:8] = (message_seq % 65536).to_bytes(2, "big")
    frame[8:12] = int(record["timestamp"]).to_bytes(4, "big")
    frame[12:15] = int(record["target_id"], 16).to_bytes(3, "big")

    status_flags = 0
    if record.get("on_ground"):
        status_flags |= 1 << 0
    if record.get("altitude_is_geometric"):
        status_flags |= 1 << 1
    if record.get("timestamp_fallback"):
        status_flags |= 1 << 2

    validity_flags = 0

    callsign = record.get("callsign")
    if callsign is not None:
        encoded_callsign = callsign.encode("ascii")
        if not 1 <= len(encoded_callsign) <= 8:
            raise ValueError(f"callsign must be 1-8 ASCII bytes: {callsign!r}")
        frame[15:15 + len(encoded_callsign)] = encoded_callsign
        validity_flags |= 1 << 6

    lat = record.get("lat")
    if lat is not None:
        latitude_code = _q((float(lat) + 90.0) / 180.0 * ((1 << 22) - 1))
        if not 0 <= latitude_code <= (1 << 22) - 1:
            raise ValueError(f"latitude_code out of range: {latitude_code}")
        frame[23:26] = latitude_code.to_bytes(3, "big")
        validity_flags |= 1 << 0

    lon = record.get("lon")
    if lon is not None:
        longitude_code = _q((float(lon) + 180.0) / 360.0 * ((1 << 22) - 1))
        if not 0 <= longitude_code <= (1 << 22) - 1:
            raise ValueError(f"longitude_code out of range: {longitude_code}")
        frame[26:29] = longitude_code.to_bytes(3, "big")
        validity_flags |= 1 << 1

    altitude = record.get("altitude")
    if altitude is not None:
        altitude_code = _q(float(altitude) + 1000.0)
        if not 0 <= altitude_code <= 65535:
            raise ValueError(f"altitude_code out of range: {altitude_code}")
        frame[29:31] = altitude_code.to_bytes(2, "big")
        validity_flags |= 1 << 2

    speed = record.get("speed")
    if speed is not None:
        speed_code = _q(float(speed) / 0.1)
        if not 0 <= speed_code <= 65535:
            raise ValueError(f"speed_code out of range: {speed_code}")
        frame[31:33] = speed_code.to_bytes(2, "big")
        validity_flags |= 1 << 3

    heading = record.get("heading")
    if heading is not None:
        heading_code = _q(float(heading) / 0.01)
        if not 0 <= heading_code <= 35999:
            raise ValueError(f"heading_code out of range: {heading_code}")
        frame[33:35] = heading_code.to_bytes(2, "big")
        validity_flags |= 1 << 4

    vertical_rate = record.get("vertical_rate")
    if vertical_rate is not None:
        vertical_rate_code = _q((float(vertical_rate) + 327.68) / 0.01)
        if not 0 <= vertical_rate_code <= 65535:
            raise ValueError(f"vertical_rate_code out of range: {vertical_rate_code}")
        frame[35:37] = vertical_rate_code.to_bytes(2, "big")
        validity_flags |= 1 << 5

    frame[37] = status_flags
    frame[38] = validity_flags

    checksum = calculate_checksum(bytes(frame[:39]))
    frame[39:41] = checksum.to_bytes(2, "big")

    return bytes(frame)


def decode_position_message(data: bytes) -> dict[str, Any]:
    """检查帧接收条件并恢复接收方结构化记录。"""
    errors: list[str] = []

    if len(data) != FRAME_SIZE:
        return {
            "message_valid": False,
            "errors": ["LENGTH_ERROR"],
            "raw_length": len(data),
        }

    magic = int.from_bytes(data[0:2], "big")
    version = data[2]
    message_type = data[3]
    message_length = int.from_bytes(data[4:6], "big")
    message_seq = int.from_bytes(data[6:8], "big")
    timestamp = int.from_bytes(data[8:12], "big")
    target_id_int = int.from_bytes(data[12:15], "big")
    target_id = f"{target_id_int:06x}"

    callsign_bytes = data[15:23]
    latitude_code = int.from_bytes(data[23:26], "big")
    longitude_code = int.from_bytes(data[26:29], "big")
    altitude_code = int.from_bytes(data[29:31], "big")
    speed_code = int.from_bytes(data[31:33], "big")
    heading_code = int.from_bytes(data[33:35], "big")
    vertical_rate_code = int.from_bytes(data[35:37], "big")
    status_flags = data[37]
    validity_flags = data[38]
    received_checksum = int.from_bytes(data[39:41], "big")
    expected_checksum = calculate_checksum(data[:39])

    if magic != 0x4453:
        errors.append("MAGIC_ERROR")
    if version != 1:
        errors.append("VERSION_ERROR")
    if message_type != 1:
        errors.append("MESSAGE_TYPE_ERROR")
    if message_length != FRAME_SIZE:
        errors.append("LENGTH_ERROR")
    if received_checksum != expected_checksum:
        errors.append("CHECKSUM_ERROR")
    if latitude_code >> 22 != 0 or longitude_code >> 22 != 0:
        errors.append("RESERVED_BITS_ERROR")
    if status_flags & 0b11111000:
        errors.append("RESERVED_BITS_ERROR")
    if validity_flags & 0b10000000:
        errors.append("RESERVED_BITS_ERROR")

    lat_valid = bool(validity_flags & (1 << 0))
    lon_valid = bool(validity_flags & (1 << 1))
    altitude_valid = bool(validity_flags & (1 << 2))
    speed_valid = bool(validity_flags & (1 << 3))
    heading_valid = bool(validity_flags & (1 << 4))
    vertical_rate_valid = bool(validity_flags & (1 << 5))
    callsign_valid = bool(validity_flags & (1 << 6))

    if not lat_valid and latitude_code != 0:
        errors.append("FLAG_VALUE_INCONSISTENCY")
    if not lon_valid and longitude_code != 0:
        errors.append("FLAG_VALUE_INCONSISTENCY")
    if not altitude_valid and altitude_code != 0:
        errors.append("FLAG_VALUE_INCONSISTENCY")
    if not speed_valid and speed_code != 0:
        errors.append("FLAG_VALUE_INCONSISTENCY")
    if not heading_valid and heading_code != 0:
        errors.append("FLAG_VALUE_INCONSISTENCY")
    if not vertical_rate_valid and vertical_rate_code != 0:
        errors.append("FLAG_VALUE_INCONSISTENCY")
    if not callsign_valid and any(callsign_bytes):
        errors.append("FLAG_VALUE_INCONSISTENCY")

    if timestamp == 0:
        errors.append("REQUIRED_FIELD_MISSING")
    if target_id_int == 0:
        # 000000 在真实环境中通常不是有效目标；课程样例保留 000001，所以这里只拦截全 0。
        errors.append("REQUIRED_FIELD_MISSING")

    callsign = None
    if callsign_valid:
        raw = callsign_bytes.rstrip(b"\x00")
        try:
            callsign = raw.decode("ascii")
        except UnicodeDecodeError:
            callsign = None
            errors.append("ENCODING_ERROR")

    lat = latitude_code / ((1 << 22) - 1) * 180.0 - 90.0 if lat_valid else None
    lon = longitude_code / ((1 << 22) - 1) * 360.0 - 180.0 if lon_valid else None
    altitude = altitude_code - 1000 if altitude_valid else None
    speed = speed_code * 0.1 if speed_valid else None
    heading = heading_code * 0.01 if heading_valid else None
    vertical_rate = vertical_rate_code * 0.01 - 327.68 if vertical_rate_valid else None

    altitude_is_geometric = bool(status_flags & (1 << 1))
    timestamp_fallback = bool(status_flags & (1 << 2))

    return {
        "message_valid": len(errors) == 0,
        "errors": errors,
        "magic": magic,
        "version": version,
        "message_type": message_type,
        "message_length": message_length,
        "message_seq": message_seq,
        "timestamp": timestamp,
        "target_id": target_id,
        "callsign": callsign,
        "lat": lat,
        "lon": lon,
        "altitude": altitude,
        "alt_type": "geo" if altitude_is_geometric else "baro",
        "on_ground": bool(status_flags & 1),
        "speed": speed,
        "heading": heading,
        "vertical_rate": vertical_rate,
        "status_flags": status_flags,
        "validity_flags": validity_flags,
        "timestamp_source": "last_contact" if timestamp_fallback else "position_time",
        "timestamp_fallback": timestamp_fallback,
        "altitude_is_geometric": altitude_is_geometric,
        "latitude_code": latitude_code,
        "longitude_code": longitude_code,
        "altitude_code": altitude_code,
        "speed_code": speed_code,
        "heading_code": heading_code,
        "vertical_rate_code": vertical_rate_code,
        "received_checksum": received_checksum,
        "expected_checksum": expected_checksum,
    }