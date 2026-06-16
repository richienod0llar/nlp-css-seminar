#!/bin/bash
# Request an interactive GPU session on LRZ (general partition, 1x H100, 2 hours)
# Usage: bash scripts/request_gpu.sh
# After allocation succeeds, run: srun --pty bash

salloc -p lrz-hgx-h100-94x4 --time=0-2:00:00 --gres=gpu:1 --cpus-per-task=8 --mem=40G
