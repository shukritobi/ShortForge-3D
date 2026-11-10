@echo off
setlocal EnableExtensions
set "REPO=%USERPROFILE%\ShortForge-3D"
set "PY=%REPO%\.venv-tts\Scripts\python.exe"
echo ShortForge - ONE-TIME OPTIONAL NVIDIA PYTORCH CUDA SETUP
echo Only modifies the isolated .venv-tts environment, never system Python.
if not exist "%PY%" (
 echo [ERROR] Install .venv-tts with Qwen first.
 pause
 exit /b 1
)
"%PY%" -c "import torch; print(torch.__version__,torch.cuda.is_available())"
echo.
echo Installing official matching PyTorch 2.11.0 + TorchAudio 2.11.0 CUDA 12.8 wheels.
echo Official source: https://pytorch.org/get-started/previous-versions/
"%PY%" -m pip install --upgrade --force-reinstall --no-deps torch==2.11.0 torchaudio==2.11.0 --index-url https://download.pytorch.org/whl/cu128
if errorlevel 1 (
 echo [ERROR] CUDA install failed; see preceding pip error. Environment not verified.
 pause
 exit /b 2
)
"%PY%" -c "import torch,torchaudio; assert torch.cuda.is_available(), 'CUDA still unavailable'; print('CUDA ready:',torch.__version__,torch.cuda.get_device_name(0),'torchaudio:',torchaudio.__version__)"
if errorlevel 1 (
 echo [ERROR] CUDA not ready. Driver/toolkit compatibility needs inspection.
 pause
 exit /b 3
)
echo [OK] CUDA-enabled Qwen should now use the NVIDIA GPU.
pause
exit /b 0
