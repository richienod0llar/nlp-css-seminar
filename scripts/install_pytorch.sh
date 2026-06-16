#!/bin/bash
# Install PyTorch for LRZ GPU nodes (CUDA driver 12.2 / toolkit 12.6).
# Run after: conda activate sig-llm
# Do NOT install torch from PyPI default index (may pull cu130 and break on LRZ).

set -euo pipefail

pip install torch==2.11.0+cu126 torchvision==0.26.0+cu126 torchaudio==2.11.0+cu126 \
  --index-url https://download.pytorch.org/whl/cu126

echo "Installed: $(python -c 'import torch; print(torch.__version__, torch.version.cuda)')"
