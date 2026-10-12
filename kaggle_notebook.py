# OCR Pipeline - Ward-42 Survey PDFs
# Kaggle Notebook: GPU Accelerated Full Pipeline Run
# Dataset: rk9098/ward42-surveys

# ============================================================
# STEP 1: Install GPU dependencies
# ============================================================
!pip install -q \
  pypdfium2 \
  paddlepaddle-gpu \
  paddleocr \
  opencv-contrib-python \
  rapidfuzz \
  transformers \
  accelerate \
  ms-swift \
  torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 \
  scikit-learn \
  Pillow \
  pandas \
  numpy \
  sentencepiece \
  protobuf \
  jsonlines \
  tqdm \
  einops \
  datasets

# ============================================================
# STEP 2: Environment setup
# ============================================================
import os, sys, json, time, subprocess
from pathlib import Path

# Kaggle paths
PDF_DIR = Path("/kaggle/input/ward42-surveys/1RN-982-WARD NO-42")
CODE_DIR = Path("/kaggle/input/ocr-platform-code")  # we'll put code in a dataset
WORK_DIR = Path("/kaggle/working")
OUT_DIR = WORK_DIR / "output"
OUT_DIR.mkdir(exist_ok=True)

# Install the package
!pip install -q -e {CODE_DIR} --no-deps 2>&1 | tail -5
sys.path.insert(0, str(CODE_DIR / "src"))

# GPU config
os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["USE_HINDI_VLM"] = "1"

print(f"PDFs dir: {PDF_DIR}")
print(f"PDFs found: {len(list(PDF_DIR.glob('*.pdf')))}")
print(f"GPU: ", end="")
!nvidia-smi -L 2>/dev/null || echo "no GPU detected"
