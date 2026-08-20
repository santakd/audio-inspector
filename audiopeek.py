#!/usr/bin/env python3
"""
================================================================================
AUDIO PEEK (audiopeek.py)
================================================================================
A production-grade Command Line Interface (CLI) application designed to extract 
deep technical specifications, container headers, and metadata across a broad
spectrum of industry-standard audio formats.

Supported Formats:
  1. MP3     (MPEG-1/2/2.5 Layer III)
  2. FLAC    (Free Lossless Audio Codec)
  3. WAV     (RIFF Waveform Audio)
  4. M4A/MP4 (AAC, ALAC - Apple Lossless, Audiobooks)
  5. AAC     (Raw ADTS Stream)
  6. OPUS    (Ogg Opus Interactive Audio Codec)
  7. OGG     (Ogg Vorbis Audio)
  8. AIFF    (Audio Interchange File Format - Apple/Studio PCM)
  9. WV      (WavPack Hybrid Lossless/Lossy Audio)
 10. DSF/DFF (Direct Stream Digital / High-Res DSD Audio)

Logging:
  Automatically logs executions and diagnostics to:
  ./logs/audiopeek_DDMMMYYYY.log (rolling over each day).
================================================================================
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

# ============================================================================
# DEPENDENCY VERIFICATION & IMPORTS
# ============================================================================
# Mutagen is the underlying audio metadata processing engine. We import 
# specific class parsers for low-level audio stream introspection.
try:
    import mutagen
    from mutagen.mp3 import MP3
    from mutagen.flac import FLAC
    from mutagen.wave import WAVE
    from mutagen.mp4 import MP4
    from mutagen.aac import AAC
    from mutagen.oggopus import OggOpus
    from mutagen.oggvorbis import OggVorbis
    from mutagen.aiff import AIFF
    from mutagen.wavpack import WavPack
    from mutagen.dsf import DSF
    from mutagen.dsdiff import DSDIFF
    from mutagen.id3 import ID3NoHeaderError
except ImportError:
    print(
        "[CRITICAL] Missing required dependency 'mutagen'.\n"
        "Please install it using: pip install mutagen",
        file=sys.stderr,
    )
    sys.exit(1)


# ============================================================================
# LOGGING SYSTEM CONFIGURATION
# ============================================================================

def setup_logger() -> logging.Logger:
    """
    Initializes a production-grade rotating daily file logger.
    
    Creates a './logs' directory if it doesn't already exist and sets up a daily
    log file formatted as: logs/audiopeek_DDMMMYYYY.log (e.g., audiopeek_24May2024.log).
    
    Returns:
        logging.Logger: Configured logger instance.
    """
    log_dir = Path("logs")
    try:
        # Create logs directory safely if it does not exist
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        print(f"[FATAL] Unable to create logging directory '{log_dir}': {err}", file=sys.stderr)
        sys.exit(1)

    # Generate daily log filename using %d%b%Y (e.g., 24May2024)
    daily_filename = f"audiopeek_{datetime.now().strftime('%d%b%Y')}.log"
    log_file_path = log_dir / daily_filename

    logger = logging.getLogger("audiopeek")
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers if setup_logger is invoked more than once
    if not logger.handlers:
        try:
            file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            
            # Timestamp | Log-Level | [Module] Message
            log_format = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(log_format)
            logger.addHandler(file_handler)
        except OSError as err:
            print(f"[ERROR] Unable to open log file '{log_file_path}': {err}", file=sys.stderr)

    return logger


LOGGER = setup_logger()


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def format_size(bytes_val: int) -> str:
    """Converts a raw integer byte count into a human-readable string (KB, MB, GB)."""
    val = float(bytes_val)
    for unit in ["B", "KB", "MB", "GB"]:
        if val < 1024.0:
            return f"{val:.2f} {unit}"
        val /= 1024.0
    return f"{val:.2f} TB"


def format_duration(seconds: float) -> str:
    """Formats numeric seconds into a timestamp string: HH:MM:SS.mmm."""
    if seconds is None or seconds < 0:
        return "00:00.000"
    mins, secs = divmod(seconds, 60)
    hrs, mins = divmod(mins, 60)
    millis = int((secs - int(secs)) * 1000)
    if hrs > 0:
        return f"{int(hrs):02d}:{int(mins):02d}:{int(secs):02d}.{millis:03d}"
    return f"{int(mins):02d}:{int(secs):02d}.{millis:03d}"


def calculate_sha256(filepath: Path, block_size: int = 65536) -> str:
    """
    Computes the SHA-256 cryptographic checksum of the target file in chunks.
    This guarantees data integrity tracking without loading the whole file into RAM.
    """
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(block_size), b""):
            sha256.update(block)
    return sha256.hexdigest()


# ============================================================================
# BASE INSPECTOR CLASS
# ============================================================================

class BaseAudioInspector:
    """
    Base class providing generic file system and binary inspection utilities
    inherited by all format-specific audiopeek implementations.
    """

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.raw_file_size = filepath.stat().st_size

    def get_generic_specs(self) -> Dict[str, Any]:
        """Extracts standard OS-level file metrics and SHA-256 checksum."""
        return {
            "File Name": self.filepath.name,
            "Absolute Path": str(self.filepath.resolve()),
            "File Size": f"{format_size(self.raw_file_size)} ({self.raw_file_size:,} bytes)",
            "Last Modified": datetime.fromtimestamp(self.filepath.stat().st_mtime).isoformat(),
            "SHA-256 Hash": calculate_sha256(self.filepath),
        }


# ============================================================================
# FORMAT-SPECIFIC INSPECTOR IMPLEMENTATIONS
# ============================================================================

class MP3Inspector(BaseAudioInspector):
    """Inspects MPEG-1/2/2.5 Layer III bitstreams and ID3 tags."""

    def inspect(self) -> Dict[str, Any]:
        LOGGER.info("Executing MP3 stream inspection: %s", self.filepath)
        audio = MP3(self.filepath)
        info = audio.info

        # Bitrate Mode: CBR vs VBR determination
        bitrate_mode_str = "VBR" if getattr(info, "bitrate_mode", None) == 1 else "CBR/ABR"

        specs: Dict[str, Any] = {
            "Format": "MPEG Audio",
            "MPEG Version": f"MPEG {info.version}",
            "Layer": f"Layer {info.layer}",
            "Duration": f"{format_duration(info.length)} ({info.length:.2f}s)",
            "Bitrate": f"{int(info.bitrate / 1000)} kbps ({bitrate_mode_str})",
            "Sample Rate": f"{info.sample_rate} Hz",
            "Channels": f"{info.channels} ({'Stereo' if info.channels == 2 else 'Mono' if info.channels == 1 else 'Multi-channel'})",
            "Channel Mode": getattr(info, "mode", "Unknown"),
            "CRC Protected": "Yes" if getattr(info, "protected", False) else "No",
            "Encoder/LAME Info": getattr(info, "encoder_info", "Not Detected"),
        }

        # Extract ID3 tags (excluding raw binary blobs like artwork)
        tags_dict = {}
        if audio.tags:
            specs["ID3 Version"] = f"v2.{audio.tags.version[0]}.{audio.tags.version[1]}"
            for key, val in audio.tags.items():
                if key.startswith("APIC"):
                    tags_dict["Attached Picture (Cover)"] = f"{val.mime} ({format_size(len(val.data))})"
                else:
                    tags_dict[key] = str(val)
        else:
            specs["ID3 Version"] = "No ID3 tags present"

        return {"File Specifications": self.get_generic_specs(), "Audio Stream Details": specs, "Metadata Tags": tags_dict}


class FLACInspector(BaseAudioInspector):
    """Inspects Free Lossless Audio Codec STREAMINFO blocks and Vorbis comments."""

    def inspect(self) -> Dict[str, Any]:
        LOGGER.info("Executing FLAC stream inspection: %s", self.filepath)
        audio = FLAC(self.filepath)
        info = audio.info

        # Calculate exact average variable bitrate
        calc_bitrate = int((self.raw_file_size * 8) / info.length / 1000) if info.length > 0 else 0

        specs: Dict[str, Any] = {
            "Format": "FLAC (Free Lossless Audio Codec)",
            "Duration": f"{format_duration(info.length)} ({info.length:.2f}s)",
            "Sample Rate": f"{info.sample_rate} Hz",
            "Channels": f"{info.channels} Channel(s)",
            "Bits Per Sample": f"{info.bits_per_sample} bits (Lossless)",
            "Total Samples": f"{info.total_samples:,}",
            "Calculated Bitrate": f"{calc_bitrate} kbps (Variable)",
            "Min Block Size": f"{info.min_blocksize} samples",
            "Max Block Size": f"{info.max_blocksize} samples",
            "Min Frame Size": f"{info.min_framesize} bytes",
            "Max Frame Size": f"{info.max_framesize} bytes",
            "Stream MD5 Signature": getattr(info, "md5_signature", "N/A"),
        }

        tags_dict = {}
        if audio.tags:
            for key, val in audio.tags:
                tags_dict[key] = ", ".join(val) if isinstance(val, list) else str(val)

        if audio.pictures:
            pics = [f"{p.mime} - {p.width}x{p.height} ({format_size(len(p.data))})" for p in audio.pictures]
            tags_dict["Embedded Artwork"] = "; ".join(pics)

        if hasattr(audio, "cuesheet") and audio.cuesheet:
            specs["Embedded Cue Sheet"] = "Present"
        if hasattr(audio, "seektable") and audio.seektable:
            specs["Seek Table Points"] = len(audio.seektable.seekpoints)

        return {"File Specifications": self.get_generic_specs(), "Audio Stream Details": specs, "Vorbis Comments / Tags": tags_dict}


class WAVInspector(BaseAudioInspector):
    """Inspects RIFF / WAVE PCM headers and broadcast metadata."""

    def inspect(self) -> Dict[str, Any]:
        LOGGER.info("Executing WAV stream inspection: %s", self.filepath)
        audio = WAVE(self.filepath)
        info = audio.info

        specs: Dict[str, Any] = {
            "Format": "RIFF / WAVE Audio",
            "Duration": f"{format_duration(info.length)} ({info.length:.2f}s)",
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


class MP4Inspector(BaseAudioInspector):
    """
    Inspects MPEG-4 Part 14 containers (.m4a, .mp4, .m4b).
    Identifies whether the underlying stream is Lossy AAC or Lossless ALAC.
    """

    def inspect(self) -> Dict[str, Any]:
        LOGGER.info("Executing MP4/M4A container inspection: %s", self.filepath)
        audio = MP4(self.filepath)
        info = audio.info

        # Identify underlying codec (ALAC vs AAC)
        codec_name = "Advanced Audio Coding (AAC)"
        if getattr(info, "codec", "").lower() == "alac" or getattr(info, "bits_per_sample", 0) > 0:
            codec_name = "Apple Lossless Audio Codec (ALAC)"

        specs: Dict[str, Any] = {
            "Container": "MPEG-4 Part 14 (M4A/MP4)",
            "Audio Codec": codec_name,
            "Codec ID": getattr(info, "codec", "mp4a"),
            "Duration": f"{format_duration(info.length)} ({info.length:.2f}s)",
            "Bitrate": f"{int(info.bitrate / 1000)} kbps",
            "Sample Rate": f"{info.sample_rate} Hz",
            "Channels": f"{info.channels} Channel(s)",
            "Bits Per Sample": f"{getattr(info, 'bits_per_sample', 'N/A')} bits" if codec_name.startswith("Apple") else "16-bit equivalent (Lossy)",
        }

        # MP4 atom metadata mapping
        mp4_atom_map = {
            "\xa9nam": "Title",
            "\xa9ART": "Artist",
            "\xa9alb": "Album",
            "\xa9day": "Year/Date",
            "\xa9gen": "Genre",
            "\xa9wrt": "Composer",
            "\xa9too": "Encoding Tool",
            "cprt": "Copyright",
            "trkn": "Track Number",
            "disk": "Disc Number",
        }

        tags_dict = {}
        if audio.tags:
            for atom_key, val in audio.tags.items():
                if atom_key == "covr" and val:
                    tags_dict["Artwork"] = f"Embedded Cover Image ({format_size(len(val[0]))})"
                else:
                    human_key = mp4_atom_map.get(atom_key, atom_key)
                    tags_dict[human_key] = str(val[0]) if isinstance(val, list) and len(val) == 1 else str(val)

        return {"File Specifications": self.get_generic_specs(), "Audio Stream Details": specs, "QuickTime / MP4 Metadata": tags_dict}


class AACInspector(BaseAudioInspector):
    """Inspects raw ADTS (Audio Data Transport Stream) AAC files."""

    def inspect(self) -> Dict[str, Any]:
        LOGGER.info("Executing raw AAC ADTS inspection: %s", self.filepath)
        audio = AAC(self.filepath)
        info = audio.info

        specs: Dict[str, Any] = {
            "Format": "Advanced Audio Coding (Raw ADTS Stream)",
            "Duration": f"{format_duration(info.length)} ({info.length:.2f}s)",
            "Bitrate": f"{int(info.bitrate / 1000)} kbps",
            "Sample Rate": f"{info.sample_rate} Hz",
            "Channels": f"{info.channels} Channel(s)",
        }

        return {"File Specifications": self.get_generic_specs(), "Audio Stream Details": specs, "Metadata Tags": {"Notice": "Raw ADTS streams do not embed structured metadata tags."}}


class OpusInspector(BaseAudioInspector):
    """
    Inspects Ogg Opus bitstreams.
    Opus natively operates at 48kHz internal clock with low-latency framing.
    """

    def inspect(self) -> Dict[str, Any]:
        LOGGER.info("Executing Ogg Opus inspection: %s", self.filepath)
        audio = OggOpus(self.filepath)
        info = audio.info

        calc_bitrate = int((self.raw_file_size * 8) / info.length / 1000) if info.length > 0 else 0

        specs: Dict[str, Any] = {
            "Format": "Ogg Opus Interactive Audio",
            "Duration": f"{format_duration(info.length)} ({info.length:.2f}s)",
            "Internal Clock Rate": f"{info.sample_rate} Hz (Standard 48kHz Opus Synthesis)",
            "Channels": f"{info.channels} Channel(s)",
            "Calculated Bitrate": f"{calc_bitrate} kbps (Variable)",
            "Pre-Skip Samples": getattr(info, "preskip", "N/A"),
            "Output Gain": f"{getattr(info, 'gain', 0)} dB",
        }

        tags_dict = {}
        if audio.tags:
            for k, v in audio.tags:
                tags_dict[k] = ", ".join(v) if isinstance(v, list) else str(v)

        return {"File Specifications": self.get_generic_specs(), "Audio Stream Details": specs, "Vorbis Comments (Opus Tags)": tags_dict}


class VorbisInspector(BaseAudioInspector):
    """Inspects Ogg Vorbis bitstreams and nominal/target bitrates."""

    def inspect(self) -> Dict[str, Any]:
        LOGGER.info("Executing Ogg Vorbis inspection: %s", self.filepath)
        audio = OggVorbis(self.filepath)
        info = audio.info

        specs: Dict[str, Any] = {
            "Format": "Ogg Vorbis Audio",
            "Duration": f"{format_duration(info.length)} ({info.length:.2f}s)",
            "Bitrate (Nominal)": f"{int(info.bitrate / 1000)} kbps" if info.bitrate else "Variable",
            "Bitrate (Target Range)": f"Min: {int(getattr(info, 'bitrate_lower', 0) / 1000)} kbps | Max: {int(getattr(info, 'bitrate_upper', 0) / 1000)} kbps",
            "Sample Rate": f"{info.sample_rate} Hz",
            "Channels": f"{info.channels} Channel(s)",
            "Vorbis Version": getattr(info, "version", "0"),
        }

        tags_dict = {}
        if audio.tags:
            for k, v in audio.tags:
                tags_dict[k] = ", ".join(v) if isinstance(v, list) else str(v)

        return {"File Specifications": self.get_generic_specs(), "Audio Stream Details": specs, "Vorbis Comments": tags_dict}


class AIFFInspector(BaseAudioInspector):
    """Inspects Apple Audio Interchange File Format (AIFF/AIFC) uncompressed PCM."""

    def inspect(self) -> Dict[str, Any]:
        LOGGER.info("Executing AIFF inspection: %s", self.filepath)
        audio = AIFF(self.filepath)
        info = audio.info

        specs: Dict[str, Any] = {
            "Format": "AIFF (Audio Interchange File Format)",
            "Duration": f"{format_duration(info.length)} ({info.length:.2f}s)",
            "Sample Rate": f"{info.sample_rate} Hz",
            "Channels": f"{info.channels} Channel(s)",
            "Bits Per Sample": f"{getattr(info, 'bits_per_sample', 'N/A')} bits (Uncompressed PCM)",
            "Bitrate": f"{int(info.bitrate / 1000)} kbps",
        }

        tags_dict = {}
        if audio.tags:
            for k, v in audio.tags.items():
                tags_dict[k] = str(v)

        return {"File Specifications": self.get_generic_specs(), "Audio Stream Details": specs, "Embedded ID3 / AIFF Tags": tags_dict}


class WavPackInspector(BaseAudioInspector):
    """Inspects WavPack lossless and hybrid audio streams."""

    def inspect(self) -> Dict[str, Any]:
        LOGGER.info("Executing WavPack inspection: %s", self.filepath)
        audio = WavPack(self.filepath)
        info = audio.info

        calc_bitrate = int((self.raw_file_size * 8) / info.length / 1000) if info.length > 0 else 0

        specs: Dict[str, Any] = {
            "Format": "WavPack (Hybrid Lossless/Lossy Audio)",
            "Duration": f"{format_duration(info.length)} ({info.length:.2f}s)",
            "Sample Rate": f"{info.sample_rate} Hz",
            "Channels": f"{info.channels} Channel(s)",
            "Bits Per Sample": f"{getattr(info, 'bits_per_sample', 'N/A')} bits",
            "Calculated Bitrate": f"{calc_bitrate} kbps",
            "WavPack Version": getattr(info, "version", "N/A"),
        }

        tags_dict = {}
        if audio.tags:
            for k, v in audio.tags.items():
                tags_dict[k] = str(v)

        return {"File Specifications": self.get_generic_specs(), "Audio Stream Details": specs, "APEv2 / WavPack Tags": tags_dict}


class DSDInspector(BaseAudioInspector):
    """Inspects Direct Stream Digital (DSF / DSDIFF) 1-bit high-resolution audio."""

    def __init__(self, filepath: Path, is_dsdiff: bool = False):
        super().__init__(filepath)
        self.is_dsdiff = is_dsdiff

    def inspect(self) -> Dict[str, Any]:
        LOGGER.info("Executing DSD inspection: %s", self.filepath)
        
        if self.is_dsdiff:
            audio = DSDIFF(self.filepath)
            format_title = "DSDIFF (Direct Stream Digital Interchange File)"
        else:
            audio = DSF(self.filepath)
            format_title = "DSF (Direct Stream Digital Sony Format)"

        info = audio.info

        # Human-readable DSD multiplier (DSD64 = 2.8224 MHz, DSD128 = 5.6448 MHz, etc.)
        dsd_rate_label = "DSD Standard"
        if info.sample_rate == 2822400:
            dsd_rate_label = "DSD64 (64x 44.1kHz = 2.8224 MHz)"
        elif info.sample_rate == 5644800:
            dsd_rate_label = "DSD128 (128x 44.1kHz = 5.6448 MHz)"
        elif info.sample_rate == 11289600:
            dsd_rate_label = "DSD256 (256x 44.1kHz = 11.2896 MHz)"
        elif info.sample_rate == 22579200:
            dsd_rate_label = "DSD512 (512x 44.1kHz = 22.5792 MHz)"

        specs: Dict[str, Any] = {
            "Format": format_title,
            "Duration": f"{format_duration(info.length)} ({info.length:.2f}s)",
            "DSD Sampling Frequency": f"{info.sample_rate:,} Hz -> {dsd_rate_label}",
            "Bit Depth": "1-bit Delta-Sigma Modulation",
            "Channels": f"{info.channels} Channel(s)",
            "Bitrate": f"{int(info.bitrate / 1000)} kbps",
        }

        tags_dict = {}
        if audio.tags:
            for k, v in audio.tags.items():
                tags_dict[k] = str(v)

        return {"File Specifications": self.get_generic_specs(), "Audio Stream Details": specs, "DSD Metadata Tags": tags_dict}


# ============================================================================
# RENDERING & OUTPUT FORMATTING
# ============================================================================

def render_terminal_output(data: Dict[str, Any]) -> None:
    """
    Renders structured dictionary data as a clean, aligned, human-readable terminal report.
    """
    width = 84
    separator = "=" * width
    sub_sep = "-" * width

    print(f"\n{separator}")
    print(f"{'AUDIO FILE SPECIFICATION REPORT':^{width}}")
    print(f"{separator}")

    for section_title, section_content in data.items():
        print(f"\n[*] {section_title.upper()}")
        print(sub_sep)

        if isinstance(section_content, dict) and section_content:
            max_key_len = max(len(str(k)) for k in section_content.keys())
            for k, v in section_content.items():
                print(f"  {str(k).ljust(max_key_len + 3)}: {v}")
        elif isinstance(section_content, dict) and not section_content:
            print("  (None detected)")
        else:
            print(f"  {section_content}")

    print(f"\n{separator}\n")


# ============================================================================
# INSPECTION CONTROLLER & ROUTER
# ============================================================================

def resolve_inspector(path: Path) -> Optional[BaseAudioInspector]:
    """
    Examines the file extension and header to return the appropriate inspector class.
    Handles ambiguous extensions (e.g., .ogg containing Opus vs Vorbis).
    """
    ext = path.suffix.lower()

    if ext == ".mp3":
        return MP3Inspector(path)
    elif ext == ".flac":
        return FLACInspector(path)
    elif ext in [".wav", ".wave"]:
        return WAVInspector(path)
    elif ext in [".m4a", ".mp4", ".m4b", ".m4p", ".alac"]:
        return MP4Inspector(path)
    elif ext == ".aac":
        return AACInspector(path)
    elif ext == ".opus":
        return OpusInspector(path)
    elif ext == ".ogg" or ext == ".oga":
        # Disambiguate Ogg container contents (Opus vs Vorbis)
        try:
            return OpusInspector(path)
        except Exception:
            return VorbisInspector(path)
    elif ext in [".aiff", ".aif", ".aifc"]:
        return AIFFInspector(path)
    elif ext == ".wv":
        return WavPackInspector(path)
    elif ext == ".dsf":
        return DSDInspector(path, is_dsdiff=False)
    elif ext == ".dff":
        return DSDInspector(path, is_dsdiff=True)
    
    return None


def inspect_file(file_path_str: str) -> Optional[Dict[str, Any]]:
    """
    Validates input parameters, checks system permissions, invokes the appropriate
    inspector, and handles all error conditions.
    """
    path = Path(file_path_str)

    # 1. Existence and File System Validation
    if not path.exists():
        LOGGER.error("File does not exist: %s", path)
        print(f"[Error] The target file '{path}' does not exist.", file=sys.stderr)
        return None

    if not path.is_file():
        LOGGER.error("Target path is not a file: %s", path)
        print(f"[Error] '{path}' is a directory or special device, not a valid audio file.", file=sys.stderr)
        return None

    if path.stat().st_size == 0:
        LOGGER.error("Zero-byte file rejected: %s", path)
        print(f"[Error] '{path}' is completely empty (0 bytes).", file=sys.stderr)
        return None

    if not os.access(path, os.R_OK):
        LOGGER.error("Permission denied reading file: %s", path)
        print(f"[Error] Read access permission denied for '{path}'.", file=sys.stderr)
        return None

    # 2. Inspector Resolution
    inspector = resolve_inspector(path)
    if inspector is None:
        supported_list = ".mp3, .flac, .wav, .m4a, .aac, .opus, .ogg, .aiff, .wv, .dsf, .dff"
        LOGGER.error("Unsupported file extension '%s' for file: %s", path.suffix, path)
        print(
            f"[Error] Unsupported format '{path.suffix}'.\n"
            f"Supported extensions are:\n  {supported_list}",
            file=sys.stderr,
        )
        return None

    # 3. Execution & Error Handling
    try:
        data = inspector.inspect()
        LOGGER.info("Successfully analyzed: %s", path)
        return data
    except ID3NoHeaderError as err:
        LOGGER.exception("ID3 header error on %s: %s", path, err)
        print(f"[Error] Missing or damaged ID3 header: {err}", file=sys.stderr)
        return None
    except mutagen.MutagenError as err:
        LOGGER.exception("Mutagen parser failure on %s: %s", path, err)
        print(f"[Error] Stream parsing failed (corrupted or malformed bitstream): {err}", file=sys.stderr)
        return None
    except Exception as err:
        LOGGER.exception("Unexpected system exception on %s: %s", path, err)
        print(f"[Fatal Error] An unexpected error occurred: {err}", file=sys.stderr)
        return None


# ============================================================================
# CLI INTERFACE & MAIN ENTRYPOINT
# ============================================================================

def build_parser() -> argparse.ArgumentParser:
    """Configures the command line interface arguments."""
    parser = argparse.ArgumentParser(
        prog="audiopeek",
        description="Production CLI audio inspection tool for audio specifications, codecs, and tags.",
        epilog="Daily logs are recorded to: ./logs/audiopeek_DDMMMYYYY.log",
    )
    parser.add_argument(
        "file",
        help="Path to the audio file to inspect (.mp3, .flac, .wav, .m4a, .aac, .opus, .ogg, .aiff, .wv, .dsf, .dff)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output the specification report in raw JSON format",
    )
    return parser


def main() -> int:
    """Main application lifecycle controller."""
    parser = build_parser()
    args = parser.parse_args()

    LOGGER.info("CLI invocation: args=%s", vars(args))

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
        LOGGER.warning("Execution interrupted by user via SIGINT.")
        print("\n[!] Operation cancelled by user.", file=sys.stderr)
        sys.exit(130)
        