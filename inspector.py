#!/usr/bin/env python3
"""
inspector - Audio File Specification & Metadata Inspector
Supported formats: MP3, WAV, FLAC

1. Basic Terminal Output

python3 inspector.py sample.mp3
python3 inspector.py track.flac
python3 inspector.py recording.wav

2. JSON Output Mode (ideal for scripting or CI/CD pipelines)

python3inspector.py track.flac --json

"""

import os
import sys
import json
import hashlib
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Third-party audio metadata engine
try:
    import mutagen
    from mutagen.mp3 import MP3, HeaderNotFoundError
    from mutagen.flac import FLAC, FLACNoHeaderError
    from mutagen.wave import WAVE
    from mutagen.id3 import ID3NoHeaderError
except ImportError:
    print(
        "[CRITICAL] Missing dependency 'mutagen'. Install it via: pip install mutagen",
        file=sys.stderr,
    )
    sys.exit(1)


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logger() -> logging.Logger:
    """
    Configures and returns a production-grade logger.
    Creates a logs folder and generates daily log files named: inspector_ddmmmyyyy.log
    """
    log_dir = Path("logs")
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"[FATAL] Could not create log directory '{log_dir}': {e}", file=sys.stderr)
        sys.exit(1)

    # Date pattern: ddmmmyyyy -> e.g., 24May2024
    log_filename = f"inspector_{datetime.now().strftime('%d%b%Y')}.log"
    log_path = log_dir / log_filename

    logger = logging.getLogger("inspector")
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers if setup is called multiple times
    if not logger.handlers:
        # File Handler (Detailed debugging info)
        try:
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except OSError as e:
            print(f"[ERROR] Could not open log file '{log_path}': {e}", file=sys.stderr)

    return logger


LOGGER = setup_logger()


# ============================================================================
# HELPER UTILITIES
# ============================================================================

def format_size(bytes_val: int) -> str:
    """Convert bytes to human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} TB"


def format_duration(seconds: float) -> str:
    """Convert seconds to HH:MM:SS.mmm format."""
    mins, secs = divmod(seconds, 60)
    hrs, mins = divmod(mins, 60)
    millis = int((secs - int(secs)) * 1000)
    if hrs > 0:
        return f"{int(hrs):02d}:{int(mins):02d}:{int(secs):02d}.{millis:03d}"
    return f"{int(mins):02d}:{int(secs):02d}.{millis:03d}"


def calculate_sha256(filepath: Path, block_size: int = 65536) -> str:
    """Compute SHA-256 hash for file integrity identification."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(block_size), b""):
            sha256.update(block)
    return sha256.hexdigest()


# ============================================================================
# FORMAT INSPECTORS
# ============================================================================

class AudioInspector:
    """Base Inspector with shared metadata extraction capabilities."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.raw_file_size = filepath.stat().st_size

    def get_generic_specs(self) -> Dict[str, Any]:
        """Extract generic filesystem details."""
        return {
            "File Name": self.filepath.name,
            "Absolute Path": str(self.filepath.resolve()),
            "File Size": f"{format_size(self.raw_file_size)} ({self.raw_file_size:,} bytes)",
            "Last Modified": datetime.fromtimestamp(self.filepath.stat().st_mtime).isoformat(),
            "SHA-256 Hash": calculate_sha256(self.filepath),
        }


class MP3Inspector(AudioInspector):
    """Deep inspection for MPEG Audio Layer III files."""

    def inspect(self) -> Dict[str, Any]:
        LOGGER.info("Starting MP3 inspection for: %s", self.filepath)
        audio = MP3(self.filepath)

        info = audio.info
        specs: Dict[str, Any] = {
            "Format": "MPEG Audio",
            "MPEG Version": f"MPEG {info.version}",
            "Layer": f"Layer {info.layer}",
            "Duration": f"{format_duration(info.length)} ({info.length:.2f} seconds)",
            "Bitrate": f"{int(info.bitrate / 1000)} kbps ({'VBR' if info.bitrate_mode == 1 else 'CBR/ABR'})",
            "Sample Rate": f"{info.sample_rate} Hz",
            "Channels": f"{info.channels} ({'Stereo' if info.channels == 2 else 'Mono' if info.channels == 1 else 'Multi-channel'})",
            "Channel Mode": getattr(info, "mode", "Unknown"),
            "CRC Protected": "Yes" if getattr(info, "protected", False) else "No",
            "Encoder/LAME Info": getattr(info, "encoder_info", "Not Detected"),
        }

        # ID3 Tag extraction
        tags_dict = {}
        if audio.tags:
            specs["ID3 Version"] = f"v2.{audio.tags.version[0]}.{audio.tags.version[1]}"
            for key, val in audio.tags.items():
                # Avoid binary frames dump (like APIC/pictures) in terminal
                if key.startswith("APIC"):
                    tags_dict["Attached Picture (Cover)"] = f"{val.mime} ({format_size(len(val.data))})"
                else:
                    tags_dict[key] = str(val)
        else:
            specs["ID3 Version"] = "No ID3 tags found"

        return {"File Specifications": self.get_generic_specs(), "Audio Stream Details": specs, "Metadata Tags": tags_dict}


class FLACInspector(AudioInspector):
    """Deep inspection for Free Lossless Audio Codec files."""

    def inspect(self) -> Dict[str, Any]:
        LOGGER.info("Starting FLAC inspection for: %s", self.filepath)
        audio = FLAC(self.filepath)
        info = audio.info

        specs: Dict[str, Any] = {
            "Format": "FLAC (Free Lossless Audio Codec)",
            "Duration": f"{format_duration(info.length)} ({info.length:.2f} seconds)",
            "Sample Rate": f"{info.sample_rate} Hz",
            "Channels": f"{info.channels} Channel(s)",
            "Bits Per Sample": f"{info.bits_per_sample} bits",
            "Total Samples": f"{info.total_samples:,}",
            "Calculated Bitrate": f"{int((self.raw_file_size * 8) / info.length / 1000)} kbps (Variable)",
            "Min Block Size": f"{info.min_blocksize} samples",
            "Max Block Size": f"{info.max_blocksize} samples",
            "Min Frame Size": f"{info.min_framesize} bytes",
            "Max Frame Size": f"{info.max_framesize} bytes",
            "Stream MD5 Signature": info.md5_signature if hasattr(info, "md5_signature") else "N/A",
        }

        # Vorbis comments / metadata
        tags_dict = {}
        if audio.tags:
            for key, val in audio.tags:
                tags_dict[key] = ", ".join(val) if isinstance(val, list) else str(val)

        # Embedded Pictures
        if audio.pictures:
            pics = [f"{p.mime} - {p.width}x{p.height} ({format_size(len(p.data))})" for p in audio.pictures]
            tags_dict["Embedded Artwork"] = "; ".join(pics)

        # CUESHEET & Seektables
        if hasattr(audio, "cuesheet") and audio.cuesheet:
            specs["Embedded Cue Sheet"] = "Present"
        if hasattr(audio, "seektable") and audio.seektable:
            specs["Seek Table Points"] = len(audio.seektable.seekpoints)

        return {"File Specifications": self.get_generic_specs(), "Audio Stream Details": specs, "Vorbis Comments / Tags": tags_dict}


class WAVInspector(AudioInspector):
    """Deep inspection for Waveform Audio File Format (WAV/RIFF)."""

    def inspect(self) -> Dict[str, Any]:
        LOGGER.info("Starting WAV inspection for: %s", self.filepath)
        audio = WAVE(self.filepath)
        info = audio.info

        specs: Dict[str, Any] = {
            "Format": "RIFF / WAVE Audio",
            "Duration": f"{format_duration(info.length)} ({info.length:.2f} seconds)",
            "Sample Rate": f"{info.sample_rate} Hz",
            "Channels": f"{info.channels} Channel(s)",
            "Bits Per Sample": f"{getattr(info, 'bits_per_sample', 'N/A')} bits",
            "Bitrate": f"{int(info.bitrate / 1000)} kbps",
        }

        tags_dict = {}
        if audio.tags:
            for k, v in audio.tags.items():
                tags_dict[k] = str(v)

        return {"File Specifications": self.get_generic_specs(), "Audio Stream Details": specs, "RIFF / ID3 Tags": tags_dict}


# ============================================================================
# RENDERING / OUTPUT
# ============================================================================

def render_terminal_output(data: Dict[str, Any]) -> None:
    """Prints cleanly structured, aligned tables in standard output."""
    separator = "=" * 80
    sub_sep = "-" * 80

    print(f"\n{separator}")
    print(f"{'AUDIO INSPECTOR REPORT':^80}")
    print(f"{separator}")

    for section_title, section_content in data.items():
        print(f"\n[+] {section_title.upper()}")
        print(sub_sep)

        if isinstance(section_content, dict) and section_content:
            max_key_len = max(len(k) for k in section_content.keys())
            for k, v in section_content.items():
                print(f"  {k.ljust(max_key_len + 3)}: {v}")
        elif isinstance(section_content, dict) and not section_content:
            print("  (None detected)")
        else:
            print(f"  {section_content}")

    print(f"\n{separator}\n")


# ============================================================================
# CORE CONTROLLER
# ============================================================================

def inspect_file(file_path_str: str) -> Optional[Dict[str, Any]]:
    """Validates, selects the right inspector, and handles all error conditions."""
    path = Path(file_path_str)

    # 1. Existence and accessibility checks
    if not path.exists():
        LOGGER.error("File not found: %s", path)
        print(f"[Error] The file '{path}' does not exist.", file=sys.stderr)
        return None

    if not path.is_file():
        LOGGER.error("Target path is not a file: %s", path)
        print(f"[Error] '{path}' is a directory or special file, not an audio file.", file=sys.stderr)
        return None

    if path.stat().st_size == 0:
        LOGGER.error("File is empty (0 bytes): %s", path)
        print(f"[Error] File '{path}' is empty (0 bytes).", file=sys.stderr)
        return None

    if not os.access(path, os.R_OK):
        LOGGER.error("Permission denied: %s", path)
        print(f"[Error] Read permission denied for file '{path}'.", file=sys.stderr)
        return None

    # 2. Extension validation & routing
    ext = path.suffix.lower()
    inspector: AudioInspector

    try:
        if ext == ".mp3":
            inspector = MP3Inspector(path)
        elif ext == ".flac":
            inspector = FLACInspector(path)
        elif ext == ".wav":
            inspector = WAVInspector(path)
        else:
            LOGGER.error("Unsupported file extension '%s' for file %s", ext, path)
            print(
                f"[Error] Unsupported format '{ext}'. Only .mp3, .wav, and .flac are supported.",
                file=sys.stderr,
            )
            return None

        # 3. Perform inspection
        result = inspector.inspect()
        LOGGER.info("Successfully inspected: %s", path)
        return result

    except (HeaderNotFoundError, FLACNoHeaderError, ID3NoHeaderError) as e:
        LOGGER.exception("Header corruption or invalid header for %s: %s", path, str(e))
        print(f"[Error] Corrupted or invalid {ext.upper()} header in '{path}': {e}", file=sys.stderr)
        return None
    except mutagen.MutagenError as e:
        LOGGER.exception("Mutagen parser error processing %s: %s", path, str(e))
        print(f"[Error] Parser failure while reading '{path}': {e}", file=sys.stderr)
        return None
    except Exception as e:
        LOGGER.exception("Unexpected system failure inspecting %s: %s", path, str(e))
        print(f"[Fatal Error] An unexpected error occurred: {e}", file=sys.stderr)
        return None


# ============================================================================
# CLI INTERFACE
# ============================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inspector",
        description="Production CLI audio inspection tool for MP3, FLAC, and WAV specifications.",
        epilog="Logs are automatically written to ./logs/inspector_DDMMMYYYY.log",
    )
    parser.add_argument(
        "file",
        help="Path to the audio file (.mp3, .flac, .wav) to inspect",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format instead of table view",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    LOGGER.info("CLI invoked with arguments: %s", vars(args))

    data = inspect_file(args.file)
    if data is None:
        return 1

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        render_terminal_output(data)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        LOGGER.warning("Execution interrupted by user.")
        print("\n[!] Inspection aborted by user.", file=sys.stderr)
        sys.exit(130)
        