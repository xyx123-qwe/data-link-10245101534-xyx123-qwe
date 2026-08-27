from __future__ import annotations

from pathlib import Path


STUDENT_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = STUDENT_PACKAGE_ROOT / "output"

REQUIRED_OUTPUTS = [
    "encoded_messages.bin",
    "decoded_partner_states.csv",
    "validation_log.csv",
    "roundtrip_report.csv",
    "decoded_multitime.csv",
    "track_table.csv",
    "current_situation.csv",
    "llm_mapping_candidate.csv",
    "verified_mapping_table.csv",
    "unified_situation.ndjson",
    "alert_log.csv",
    "quality_situation.csv",
    "m5_result_note.md",
]


def prepare_output_directory() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def _require_output(filename: str) -> None:
    path = OUTPUT_ROOT / filename
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(f"missing required output: {path}")


def parse() -> None:
    _require_output("decoded_partner_states.csv")
    _require_output("validation_log.csv")


def encode() -> None:
    _require_output("encoded_messages.bin")


def decode_validate() -> None:
    _require_output("decoded_partner_states.csv")
    _require_output("roundtrip_report.csv")


def build_tracks() -> None:
    _require_output("decoded_multitime.csv")
    _require_output("track_table.csv")
    _require_output("current_situation.csv")


def map_unified() -> None:
    _require_output("llm_mapping_candidate.csv")
    _require_output("verified_mapping_table.csv")
    _require_output("unified_situation.ndjson")


def check_quality() -> None:
    _require_output("alert_log.csv")
    _require_output("quality_situation.csv")
    _require_output("m5_result_note.md")


def export_results() -> None:
    for filename in REQUIRED_OUTPUTS:
        _require_output(filename)


def run_pipeline() -> None:
    prepare_output_directory()
    parse()
    encode()
    decode_validate()
    build_tracks()
    map_unified()
    check_quality()
    export_results()
    print("M1-M6 required outputs are present.")


def main() -> int:
    run_pipeline()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())