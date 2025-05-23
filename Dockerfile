# ---- build stage ----
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ---- runtime stage ----
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
# копируем зависимости из builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
# копируем исходники
COPY bot/ bot/

# healthcheck: простой запрос getMe
COPY bot/health.py .
HEALTHCHECK CMD python health.py || exit 1

CMD ["python", "-m", "bot.main"]
