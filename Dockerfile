FROM python:3.11-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install requirements
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt
RUN python -m pip install --no-cache-dir 'python-telegram-bot[job-queue]'

WORKDIR /app
COPY . /app
RUN python -m pip install .

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
# USER appuser

CMD ["python", "src/bot/bot.py", "bot_cfg.json"]