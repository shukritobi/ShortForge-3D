# ShortForge Narration: Qwen3-TTS first, Kokoro fallback

No Windows System.Speech, no Windows SAPI. No paid API keys.

## Model selection based on official repositories
1. Primary: Qwen3-TTS 12Hz 0.6B CustomVoice, English Ryan or Aiden.
   - Repository: https://github.com/QwenLM/Qwen3-TTS
   - Weights: https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice
   - Apache-2.0 weights. Approx 2.5 GB model repository.
   - Python API: Qwen3TTSModel.generate_custom_voice()
   - First load downloads checkpoint, later runs from cache.
2. Lightweight alternative: Kokoro-82M.
   - Repository: https://github.com/hexgrad/kokoro
   - Weights: https://huggingface.co/hexgrad/Kokoro-82M
   - Apache-2.0, default voice af_heart (English).
3. Chatterbox-Turbo: optional experiments only. Its README states the repo
   is archived/unmaintained as of August 2026. Not selected as main engine.

## One-time setup on Windows

Open PowerShell in C:\Users\User\ShortForge-3D.

First check Python 3.11 or 3.12:
    py -3.11 --version
If unavailable, install a supported Python version from python.org, then retry.
Do NOT reuse .venv (main ShortForge environment).

    py -3.11 -m venv .venv-tts
    .\.venv-tts\Scripts\python.exe -m pip install --upgrade pip
    .\.venv-tts\Scripts\python.exe -m pip install -r requirements-tts-qwen.txt

Check NVIDIA CUDA support:
    .\.venv-tts\Scripts\python.exe -c "import torch; print(torch.__version__, torch.cuda.is_available())"

If CUDA reports False, follow the current official PyTorch Windows GPU wheel
installation instructions at https://pytorch.org/get-started/locally/.
Do not guess a torch CUDA wheel version. Qwen can run on CPU but is slower.

Run the diagnostic:
    .\.venv\Scripts\python.exe scripts/pc_agent.py doctor

## Produce the first real narrated video

    .\.venv\Scripts\python.exe scripts/pc_agent.py full --tts qwen --speaker Ryan

Or the direct CLI:
    .\.venv\Scripts\python.exe -m shortforge.cli run examples/water_tower_40s.json --tts qwen --voice Ryan --out output/water_tower

The voice model is loaded once for all eight beats in .venv-tts.
Audio is generated BEFORE Blender starts the costly full render.
Each beat is time-fitted within reasonable tempo bounds and then stitched.
The full MP4 is at output/water_tower/draft.mp4.

Audio files/voice models are not committed to Git. The initial model download
needs internet access; thereafter the Hugging Face cache can be used offline.

## Faster lightweight alternative

    py -3.11 -m venv .venv-tts
    .\.venv-tts\Scripts\python.exe -m pip install -r requirements-tts-kokoro.txt
    .\.venv\Scripts\python.exe scripts/pc_agent.py full --tts kokoro --speaker af_heart

Kokoro may need eSpeak NG support for out-of-dictionary words on Windows.
Install an eSpeak NG distribution if its own dependency diagnostics request it.
Do not install Windows SAPI voices.

## Video without narration (technical test only)

    .\.venv\Scripts\python.exe scripts/pc_agent.py full --tts none

This emits a 40-second muted-audio MP4. It is NOT a finished narrated Short.

## Audio quality rules
- Listen to every beat before approving a final MP4.
- Reject missing words, mispronunciations, clipping, unnatural extreme speeding
  and inconsistent tone.
- If a beat is too long for its 4-7s shot, rewrite the beat; do not exceed
  reasonable tempo bounds.
- Word-level captions currently use approximate phrase timing; future
  Faster-Whisper forced alignment is planned.
- Save an immutable voice setting manifest for repeatable future renders.


## Verify the TTS Python environment actually sees the RTX GPU

The main PC agent's `ready_full` status checks installed packages, but not that
Qwen can accelerate on NVIDIA until this extra check is run:

```powershell
.\.venv-tts\Scripts\python.exe -c "import torch; print('torch:', torch.__version__); print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU-only')"
```

If CUDA reports False, use the **current official PyTorch Windows pip CUDA
installer** at https://pytorch.org/get-started/locally/ with your Windows
Python version, and use the corresponding CUDA-enabled torch/torchaudio
packages in `.venv-tts` only. Do not overwrite ShortForge's `.venv`.
`python scripts/pc_agent.py doctor` will now also report `tts.torch`.

Before running all 960 Blender frames, test only Qwen narration:

```powershell
.\.venv\Scripts\python.exe -m shortforge.cli audio examples/water_tower_40s.json --tts qwen --voice Ryan --out output/water_tower
```

This catches voice/model and beat-timing failures before any expensive 3D work.
