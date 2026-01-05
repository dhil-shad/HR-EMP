#!/usr/bin/env bash
# Exit on error
set -o errexit

# 1. Install dependencies
pip install -r requirements.txt

# 2. Collect static files (CSS/JS)
python manage.py collectstatic --no-input

# 3. Apply database migrations
python manage.py migrate