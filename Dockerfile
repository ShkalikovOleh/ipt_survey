FROM python:3.13-slim
# make uv avaliable
COPY --from=ghcr.io/astral-sh/uv:0.7.20 /uv /uvx /bin/

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

ADD . /app
WORKDIR /app

# Install requirements
RUN uv sync --locked --no-editable

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
# USER appuser

CMD ["uv", "run", "src/bot/posting_bot.py", "bot_cfg.json"]