#!/bin/bash
# Activate the sig-llm conda environment (run: source scripts/activate_env.sh)
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate sig-llm
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/setup_cuda_libs.sh"
