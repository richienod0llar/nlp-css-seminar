#!/bin/bash
# Same as start_vllm.sh but with verbose logging (for debugging startup failures).
export VLLM_LOGGING_LEVEL=DEBUG
exec "$(dirname "${BASH_SOURCE[0]}")/start_vllm.sh"
