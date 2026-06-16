# Source after conda activate sig-llm.
#
# LRZ H100 nodes use driver CUDA 12.2. vLLM 0.20+ links libcudart.so.13, so we:
# 1) Prefer cu12 runtime libs (compatible with the cluster driver)
# 2) Append cu13 libcudart last so vLLM extensions can load
# 3) Expose cu13 nvcc via CUDA_HOME for optional JIT builds

if [ -n "${CONDA_PREFIX:-}" ]; then
  NVLIB_ROOT="$CONDA_PREFIX/lib/python3.11/site-packages/nvidia"
  if [ -d "$NVLIB_ROOT" ]; then
    for libdir in "$NVLIB_ROOT"/*/lib; do
      case "$libdir" in
        */cu13/lib) continue ;;
        */cuda_runtime/lib|*-cu12*/lib) ;;
        *) continue ;;
      esac
      if [ -d "$libdir" ]; then
        LD_LIBRARY_PATH="${libdir}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
      fi
    done

    CU13_LIBDIR="$NVLIB_ROOT/cu13/lib"
    if [ -d "$CU13_LIBDIR" ]; then
      LD_LIBRARY_PATH="${LD_LIBRARY_PATH:+$LD_LIBRARY_PATH:}$CU13_LIBDIR"
    fi
    export LD_LIBRARY_PATH
  fi

  CUDA_NVCC_ROOT="$NVLIB_ROOT/cu13"
  if [ -x "$CUDA_NVCC_ROOT/bin/nvcc" ]; then
    export CUDA_HOME="$CUDA_NVCC_ROOT"
    export CUDA_PATH="$CUDA_NVCC_ROOT"
    PATH="$CUDA_NVCC_ROOT/bin${PATH:+:$PATH}"
    export PATH
  fi
fi
