import os
import shutil

# Auto-detect and configure Node.js runtime for yt-dlp signature decryption
POSSIBLE_NODE_PATHS = [
    r"C:\Program Files\nodejs",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\node"),
]
for p in POSSIBLE_NODE_PATHS:
    if os.path.exists(os.path.join(p, "node.exe")):
        if p not in os.environ.get("PATH", ""):
            os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")
        break

# Auto-detect and configure FFmpeg in PATH BEFORE importing pydub or yt_dlp
POSSIBLE_FFMPEG_PATHS = [
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin"),
    r"C:\ffmpeg\bin",
    r"C:\Program Files\ffmpeg\bin",
]

FFMPEG_DIR = None
for p in POSSIBLE_FFMPEG_PATHS:
    if os.path.exists(os.path.join(p, "ffmpeg.exe")):
        FFMPEG_DIR = p
        break

if FFMPEG_DIR and FFMPEG_DIR not in os.environ.get("PATH", ""):
    os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")

import yt_dlp
from pydub import AudioSegment

if FFMPEG_DIR:
    AudioSegment.converter = os.path.join(FFMPEG_DIR, "ffmpeg.exe")
    AudioSegment.ffprobe = os.path.join(FFMPEG_DIR, "ffprobe.exe")

DOWNLOAD_DIR = 'downloades'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def download_youtube_audio(url: str) -> str:
    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")
    node_exe = shutil.which("node")
    js_runtimes = {"node": {}} if node_exe else None

    # 1. Quick check: check if video is already downloaded
    try:
        ydl_info_opts = {
            "quiet": True,
            "restrictfilenames": True,
            "outtmpl": output_path,
        }
        if js_runtimes:
            ydl_info_opts["js_runtimes"] = js_runtimes

        with yt_dlp.YoutubeDL(ydl_info_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            raw_filename = ydl.prepare_filename(info)
            base_name = os.path.splitext(raw_filename)[0]
            expected_wav = f"{base_name}.wav"

            if os.path.exists(expected_wav) and os.path.getsize(expected_wav) > 10000:
                print(f"Audio already downloaded and cached: {expected_wav}")
                return expected_wav
    except Exception as e:
        print(f"Cache check notice: {e}")

    # 2. Download audio if not already available
    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "restrictfilenames": True,
        "overwrites": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
    }
    if js_runtimes:
        ydl_opts["js_runtimes"] = js_runtimes
    if FFMPEG_DIR:
        ydl_opts["ffmpeg_location"] = FFMPEG_DIR

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        raw_filename = ydl.prepare_filename(info)

    wav_filename = os.path.splitext(raw_filename)[0] + ".wav"
    if os.path.exists(wav_filename):
        return wav_filename

    if os.path.exists(raw_filename):
        return convert_to_wav(raw_filename)

    return raw_filename



SUPPORTED_EXTENSIONS = {
    ".wav", ".mp3", ".mp4", ".m4a", ".webm",
    ".ogg", ".flac", ".mkv", ".avi", ".mov", ".aac"
}

def convert_to_wav(input_path: str) -> str:
    """Convert any audio/video file to WAV format using pydub."""
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Local file not found: '{input_path}'")

    if os.path.getsize(input_path) == 0:
        raise ValueError(f"File is empty (0 bytes): '{input_path}'")

    ext = os.path.splitext(input_path)[1].lower()
    if ext and ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format '{ext}'. Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    output_path = os.path.splitext(input_path)[0] + "_converted.wav"
    if os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
        return output_path

    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)  # 16khz
    audio.export(output_path, format="wav")
    return output_path



def chunk_audio(wav_path: str, chunk_minutes: int = 10) -> list:
    audio = AudioSegment.from_file(wav_path)
    chunk_ms = chunk_minutes * 60 * 1000

    # If audio is already short (<= chunk_minutes), reuse without re-exporting
    if len(audio) <= chunk_ms:
        return [wav_path]

    chunks = []
    base_name = os.path.splitext(wav_path)[0]

    for i, start in enumerate(range(0, len(audio), chunk_ms)):
        chunk = audio[start: start + chunk_ms]
        chunk_path = f"{base_name}_chunk_{i}.wav"
        chunk.export(chunk_path, format="wav")
        chunks.append(chunk_path)

    return chunks


def process_input(source: str) -> list:
    if source.startswith("http://") or source.startswith("https://"):
        print("Detected YouTube URL. Downloading audio...")
        wav_path = download_youtube_audio(source)
    else:
        print("Detected local file. Converting to WAV...")
        wav_path = convert_to_wav(source)

    print("Chunking audio...")
    chunks = chunk_audio(wav_path)
    print(f"Audio ready — {len(chunks)} chunk(s) created.")
    return chunks


