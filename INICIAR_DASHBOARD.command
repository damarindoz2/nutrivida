#!/bin/zsh

cd "$(dirname "$0")" || exit 1
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
elif [ -f ../.venv/bin/activate ]; then
    source ../.venv/bin/activate
else
    echo "No encontré el entorno virtual. Sigue las instrucciones de README.md."
    exit 1
fi
streamlit run dashboard.py
