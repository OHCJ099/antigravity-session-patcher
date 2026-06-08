# -*- coding: utf-8 -*-
"""Antigravity Desktop conversation DB synchronizer.

Antigravity keeps two useful copies of a trajectory:

1. ``~/.gemini/antigravity/brain/<id>/.system_generated/logs/transcript.jsonl``
   — readable append-only transcript used by this patcher for scanning/preview.
2. ``~/.gemini/antigravity/conversations/<id>.db``
   — SQLite database with protobuf blobs used by the Antigravity UI.

Older builds also have ``.pb`` files.  The web UI looked successful before this
adapter because it only modified (1).  This module mirrors replacements into
(2) by recursively updating length-delimited protobuf string fields without
requiring Antigravity's private ``.proto`` schema.
"""
from __future__ import annotations

import os
import re
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional


def default_antigravity_conversations_dir() -> Path:
    return Path.home() / ".gemini" / "antigravity" / "conversations"


def extract_trajectory_id_from_transcript(file_path: str) -> Optional[str]:
    """Return ``<id>`` from ``brain/<id>/.system_generated/logs/transcript.jsonl``."""
    parts = Path(file_path).resolve().parts
    for index, part in enumerate(parts):
        if part == "brain" and index + 1 < len(parts):
            return parts[index + 1]
    return None


def conversation_db_for_transcript(file_path: str) -> Optional[Path]:
    trajectory_id = extract_trajectory_id_from_transcript(file_path)
    if not trajectory_id:
        return None
    db_path = default_antigravity_conversations_dir() / f"{trajectory_id}.db"
    return db_path if db_path.exists() else None


@dataclass
class AntigravitySyncResult:
    db_path: Optional[str] = None
    backup_path: Optional[str] = None
    fields_updated: int = 0
    blobs_updated: int = 0
    pb_path: Optional[str] = None
    pb_backup_path: Optional[str] = None
    pb_updated: bool = False
    error: Optional[str] = None

    @property
    def updated(self) -> bool:
        return self.fields_updated > 0 or self.pb_updated


def _read_varint(data: bytes, offset: int) -> tuple[int, int]:
    result = 0
    shift = 0
    pos = offset
    while pos < len(data):
        byte = data[pos]
        result |= (byte & 0x7F) << shift
        pos += 1
        if not (byte & 0x80):
            return result, pos
        shift += 7
        if shift > 70:
            raise ValueError("varint too long")
    raise ValueError("truncated varint")


def _write_varint(value: int) -> bytes:
    if value < 0:
        raise ValueError("negative varint")
    out = bytearray()
    while value >= 0x80:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


def _looks_like_utf8_text(payload: bytes) -> Optional[str]:
    if not payload:
        return ""
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return None
    # Avoid treating arbitrary control-heavy binary as text.
    printable = sum((ch.isprintable() or ch in "\r\n\t") for ch in text)
    if printable / max(len(text), 1) < 0.75:
        return None
    return text


def _replace_bytes_direct(payload: bytes, replacements: list[tuple[bytes, bytes]]) -> tuple[bytes, int]:
    updated = payload
    count = 0
    for old, new in replacements:
        if old and old in updated:
            occurrences = updated.count(old)
            updated = updated.replace(old, new)
            count += occurrences
    return updated, count


def replace_in_protobuf_blob(blob: bytes, replacements: list[tuple[bytes, bytes]], depth: int = 0) -> tuple[bytes, int]:
    """Recursively replace UTF-8 strings inside protobuf blobs.

    The parser is schema-agnostic and only rewrites when it can parse the full
    message.  Direct string payload replacement is preferred; recursive parsing
    is used for nested messages.
    """
    if not blob or not replacements:
        return blob, 0
    if depth > 32:
        return blob, 0

    out = bytearray()
    pos = 0
    replacements_done = 0

    try:
        while pos < len(blob):
            key, key_end = _read_varint(blob, pos)
            wire_type = key & 0x07
            field_number = key >> 3
            if field_number <= 0:
                raise ValueError("invalid field number")
            out.extend(blob[pos:key_end])
            pos = key_end

            if wire_type == 0:  # varint
                _, value_end = _read_varint(blob, pos)
                out.extend(blob[pos:value_end])
                pos = value_end
            elif wire_type == 1:  # fixed64
                if pos + 8 > len(blob):
                    raise ValueError("truncated fixed64")
                out.extend(blob[pos:pos + 8])
                pos += 8
            elif wire_type == 2:  # length-delimited
                length, data_start = _read_varint(blob, pos)
                data_end = data_start + length
                if data_end > len(blob):
                    raise ValueError("truncated length-delimited")
                payload = blob[data_start:data_end]

                text = _looks_like_utf8_text(payload)
                if text is not None:
                    new_payload, count = _replace_bytes_direct(payload, replacements)
                else:
                    new_payload, count = replace_in_protobuf_blob(payload, replacements, depth + 1)

                out.extend(_write_varint(len(new_payload)))
                out.extend(new_payload)
                replacements_done += count
                pos = data_end
            elif wire_type == 5:  # fixed32
                if pos + 4 > len(blob):
                    raise ValueError("truncated fixed32")
                out.extend(blob[pos:pos + 4])
                pos += 4
            else:
                raise ValueError(f"unsupported wire type {wire_type}")
    except Exception:
        # If this is not a protobuf message, still support raw UTF-8 blobs.
        return _replace_bytes_direct(blob, replacements)

    return bytes(out), replacements_done


def normalize_replacements(replacements: Iterable[tuple[str, str]]) -> list[tuple[bytes, bytes]]:
    result: list[tuple[bytes, bytes]] = []
    seen = set()
    for old, new in replacements:
        if not old or old == new:
            continue
        old_b = old.encode("utf-8")
        new_b = new.encode("utf-8")
        key = (old_b, new_b)
        if key in seen:
            continue
        seen.add(key)
        result.append(key)
    # Longest first avoids partial replacements stealing substrings.
    result.sort(key=lambda item: len(item[0]), reverse=True)
    return result


def backup_file(path: Path) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.name}.{timestamp}.bak")
    shutil.copy2(path, backup_path)
    return str(backup_path)


def sync_antigravity_conversation_store(
    transcript_path: str,
    replacements: Iterable[tuple[str, str]],
    create_backup: bool = True,
) -> AntigravitySyncResult:
    """Mirror transcript replacements into Antigravity UI storage."""
    normalized = normalize_replacements(replacements)
    db_path = conversation_db_for_transcript(transcript_path)
    result = AntigravitySyncResult(db_path=str(db_path) if db_path else None)
    if not normalized or not db_path:
        return result

    try:
        if create_backup:
            result.backup_path = backup_file(db_path)

        con = sqlite3.connect(str(db_path), timeout=10)
        try:
            con.execute("PRAGMA busy_timeout=10000")
            tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            for (table,) in tables:
                cols = con.execute(f"PRAGMA table_info({table})").fetchall()
                pk_cols = [col[1] for col in cols if col[5]]
                blob_cols = [col[1] for col in cols if (col[2] or "").lower() == "blob"]
                text_cols = [col[1] for col in cols if (col[2] or "").lower() in ("text", "varchar", "char")]
                if not pk_cols or not (blob_cols or text_cols):
                    continue

                select_cols = pk_cols + blob_cols + text_cols
                quoted = ", ".join(f"`{c}`" for c in select_cols)
                rows = con.execute(f"SELECT {quoted} FROM `{table}`").fetchall()
                for row in rows:
                    pk_values = row[:len(pk_cols)]
                    values = dict(zip(select_cols[len(pk_cols):], row[len(pk_cols):]))
                    assignments = []
                    params = []

                    for col in blob_cols:
                        value = values.get(col)
                        if not isinstance(value, (bytes, bytearray)):
                            continue
                        updated, count = replace_in_protobuf_blob(bytes(value), normalized)
                        if count > 0 and updated != value:
                            assignments.append(f"`{col}` = ?")
                            params.append(sqlite3.Binary(updated))
                            result.fields_updated += count
                            result.blobs_updated += 1

                    for col in text_cols:
                        value = values.get(col)
                        if not isinstance(value, str):
                            continue
                        updated = value
                        count = 0
                        for old_b, new_b in normalized:
                            old = old_b.decode("utf-8")
                            new = new_b.decode("utf-8")
                            if old in updated:
                                count += updated.count(old)
                                updated = updated.replace(old, new)
                        if count > 0 and updated != value:
                            assignments.append(f"`{col}` = ?")
                            params.append(updated)
                            result.fields_updated += count

                    if assignments:
                        where = " AND ".join(f"`{c}` = ?" for c in pk_cols)
                        params.extend(pk_values)
                        con.execute(f"UPDATE `{table}` SET {', '.join(assignments)} WHERE {where}", params)
            con.commit()
            if result.fields_updated:
                # Antigravity/SQLite can leave old protobuf bytes in freelist pages
                # after an UPDATE.  Those bytes are not active UI data, but raw
                # string scans make it look as if the patch failed.  Compact on a
                # best-effort basis so both the UI and on-disk file reflect the
                # same state.  Ignore lock/compatibility failures: the row updates
                # above are the important part and have already been committed.
                try:
                    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                except sqlite3.DatabaseError:
                    pass
                try:
                    con.execute("VACUUM")
                except sqlite3.DatabaseError:
                    pass
        finally:
            con.close()

        # Older Antigravity trajectories may use a standalone protobuf file.
        pb_path = db_path.with_suffix(".pb")
        result.pb_path = str(pb_path) if pb_path.exists() else None
        if pb_path.exists():
            data = pb_path.read_bytes()
            updated, count = replace_in_protobuf_blob(data, normalized)
            if count > 0 and updated != data:
                if create_backup:
                    result.pb_backup_path = backup_file(pb_path)
                pb_path.write_bytes(updated)
                result.fields_updated += count
                result.pb_updated = True
    except Exception as exc:
        result.error = str(exc)

    return result
