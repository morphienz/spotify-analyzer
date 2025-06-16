#!/usr/bin/env bash
set -e

# Install backend dependencies
python3 -m pip install -r Backend/requirements.txt

# Install frontend dependencies
(cd Frontend/spotify-analyzer && npm install)

