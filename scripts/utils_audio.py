from pathlib import Path
import shutil
import subprocess


def _ffmpeg_available() -> bool:
    return shutil.which('ffmpeg') is not None


def convert_to_mono_wav(src, dst, sample_rate: int = 44100, channels: int = 1, overwrite: bool = False) -> bool:
    """Convert audio file to WAV mono (PCM16) using ffmpeg if available.

    Returns True on success, False on failure.
    """
    src_p = Path(src)
    dst_p = Path(dst)
    if dst_p.exists() and not overwrite:
        print(f"convert_to_mono_wav: destination exists and overwrite=False: {dst_p}")
        return True

    # Ensure parent exists
    dst_p.parent.mkdir(parents=True, exist_ok=True)

    if _ffmpeg_available():
        cmd = [
            'ffmpeg',
            '-y' if overwrite else '-n',
            '-i', str(src_p),
            '-ac', str(channels),
            '-ar', str(sample_rate),
            '-acodec', 'pcm_s16le',
            str(dst_p)
        ]
        try:
            print(f"Converting with ffmpeg: {src_p} -> {dst_p} (channels={channels}, sr={sample_rate})")
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0:
                return True
            else:
                print(f"ffmpeg failed (rc={res.returncode}): {res.stderr.decode(errors='ignore')}")
        except Exception as e:
            print(f"ffmpeg conversion exception: {e}")

    # Fallback to pydub if installed
    try:
        from pydub import AudioSegment
    except Exception as e:
        print('pydub not available; cannot convert without ffmpeg. Install ffmpeg or pydub.')
        return False

    try:
        print(f"Converting with pydub: {src_p} -> {dst_p} (channels={channels}, sr={sample_rate})")
        audio = AudioSegment.from_file(str(src_p))
        # set frame_rate and channels
        audio = audio.set_frame_rate(sample_rate).set_channels(channels)
        audio.export(str(dst_p), format='wav')
        return True
    except Exception as e:
        print(f"pydub conversion failed: {e}")
        return False

