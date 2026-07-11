FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

RUN sed -i 's|http://deb.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's|http://deb.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends libpq5 postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple uv

WORKDIR /app

RUN groupadd -r appgroup && useradd -r -g appgroup -u 1001 appuser

COPY --chown=appuser:appgroup pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

COPY --chown=appuser:appgroup manage.py ./
COPY --chown=appuser:appgroup config ./config
COPY --chown=appuser:appgroup apps ./apps
COPY --chown=appuser:appgroup static ./static
COPY --chown=appuser:appgroup templates ./templates
COPY --chown=appuser:appgroup scripts ./scripts

COPY --chown=appuser:appgroup docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
