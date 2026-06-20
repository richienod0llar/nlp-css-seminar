#!/bin/bash
# Request an interactive GPU session on LRZ (general partition, 1x H100, 2 hours)
#
# Run on the LOGIN node:
#   bash scripts/request_gpu.sh
#
# After salloc succeeds, open a new terminal (or note the job ID) and run:
#   squeue -u $USER                    # find JOBID
#   srun --jobid=<JOBID> --overlap --pty bash
#   nvidia-smi
#   source ~/nlp-css-seminar/scripts/activate_env.sh

salloc -p lrz-hgx-h100-94x4 \
  --time=0-2:00:00 \
  --gres=gpu:1 \
  --cpus-per-task=8 \
  --mem=40G
