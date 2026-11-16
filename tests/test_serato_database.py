"""Serato database V2 TLV parsing + path normalisation (golden binary).

Covers _iter_tlv (the binary parser that touches the user's real Serato DB)
and normalize_rel_path (drive-relative comparison used by diff/duplicates).
"""
import struct

from serato_automation.serato_database import (
    _iter_tlv, _encode_tlv, _decode_text, _encode_text, normalize_rel_path,
)


def _tlv(tag: str, value: bytes) -> bytes:
    return _encode_tlv(tag, value)


def test_iter_tlv_round_trip():
    blob = _tlv("vrsn", b"1.0\x00") + _tlv("otrk", _tlv("tsng", _encode_text("Levels")) + _tlv("tart", _encode_text("Avicii")))
    tags = [(tag, value) for tag, value in _iter_tlv(blob)]
    assert tags[0][0] == "vrsn"
    assert tags[1][0] == "otrk"
    # The otrk value is itself a TLV stream.
    inner = [(t, v) for t, v in _iter_tlv(tags[1][1])]
    assert inner[0][0] == "tsng"
    assert _decode_text(inner[0][1]) == "Levels"
    assert inner[1][0] == "tart"
    assert _decode_text(inner[1][1]) == "Avicii"


def test_iter_tlv_truncated_safe():
    # A blob that cuts off mid-record must not raise — it stops at the last
    # complete record (8-byte header + value).
    blob = _tlv("vrsn", b"1.0\x00") + b"tsn"  # garbage tail
    tags = list(_iter_tlv(blob))
    assert len(tags) == 1
    assert tags[0][0] == "vrsn"


def test_encode_text_utf16be_no_bom():
    assert _encode_text("Levels") == "Levels".encode("utf-16-be")
    # Empty string -> empty bytes (no BOM, no terminator).
    assert _encode_text("") == b""


def test_normalize_rel_path_strips_drive_and_case():
    assert normalize_rel_path("E:\\selezioni\\File.mp3") == "selezioni/file.mp3"
    assert normalize_rel_path("selezioni/File.mp3") == "selezioni/file.mp3"
    assert normalize_rel_path("F:/Music/A.mp3") == normalize_rel_path("E:\\Music\\A.mp3")
    assert normalize_rel_path("") == ""
