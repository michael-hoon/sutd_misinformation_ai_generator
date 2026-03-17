#!/bin/bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
uvicorn main:app --reload --port 8000