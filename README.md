## audio-inspector

### AUDIO INSPECTOR (inspector.py)

A production-grade Command Line Interface (CLI) application designed to extract 
deep technical specifications, container headers, and metadata across a broad
spectrum of industry-standard audio formats.

### Supported Formats:
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

### Logging:
  Automatically logs executions and diagnostics to:
  ./logs/inspector_DDMMMYYYY.log (rolling over each day).
 
### Sample Reports

                          AUDIO FILE SPECIFICATION REPORT                           


[*] FILE SPECIFICATIONS
------------------------------------------------------------------------------------
  File Name       : sott.mp3
  Absolute Path   : /Users/sd/src/sott.mp3
  File Size       : 1.72 MB (1,806,880 bytes)
  Last Modified   : 2026-08-18T23:54:32.714260
  SHA-256 Hash    : 8e3e0e53e58e0a97ce0af52971efd60e0952223174f8544d52c6fa33bf608faf

[*] AUDIO STREAM DETAILS
------------------------------------------------------------------------------------
  Format              : MPEG Audio
  MPEG Version        : MPEG 1
  Layer               : Layer 3
  Duration            : 01:52.901 (112.90s)
  Bitrate             : 128 kbps (VBR)
  Sample Rate         : 44100 Hz
  Channels            : 2 (Stereo)
  Channel Mode        : 0
  CRC Protected       : No
  Encoder/LAME Info   : 
  ID3 Version         : v2.2.4

[*] METADATA TAGS
------------------------------------------------------------------------------------
  TSSE   : Lavf61.7.100

------------------------------------------------------------------------------------

                                                                                    


                          AUDIO FILE SPECIFICATION REPORT                           


[*] FILE SPECIFICATIONS
------------------------------------------------------------------------------------
  File Name       : sott.flac
  Absolute Path   : /Users/sd/src/sott.flac
  File Size       : 15.20 MB (15,941,366 bytes)
  Last Modified   : 2026-08-19T00:28:09.846327
  SHA-256 Hash    : acb852cc7d4f323c92b0d5d6c8ada4c221577c96f27eda4fbce293f98c708770

[*] AUDIO STREAM DETAILS
------------------------------------------------------------------------------------
  Format                 : FLAC (Free Lossless Audio Codec)
  Duration               : 01:52.301 (112.30s)
  Sample Rate            : 96000 Hz
  Channels               : 2 Channel(s)
  Bits Per Sample        : 24 bits (Lossless)
  Total Samples          : 10,780,981
  Calculated Bitrate     : 1135 kbps (Variable)
  Min Block Size         : 8192 samples
  Max Block Size         : 8192 samples
  Min Frame Size         : 354 bytes
  Max Frame Size         : 15147 bytes
  Stream MD5 Signature   : 60936442855784762608247054654467319081

[*] VORBIS COMMENTS / TAGS
------------------------------------------------------------------------------------
  encoder   : Lavf63.1.101

------------------------------------------------------------------------------------
