#!/bin/bash
# Quick deploy — same as pull_to_prod.sh but shorter output
# Just runs the full deploy. Always safe to run.
set -e
bash /opt/pureleven/scripts/pull_to_prod.sh
