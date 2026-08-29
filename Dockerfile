FROM python:3.12-slim@sha256:27f90d79cc85e9b7b2560063ef44fa0e9eaae7a7c3f5a9f74563065c5477cc24 AS build
WORKDIR /build
COPY pyproject.toml .
COPY src ./src
RUN pip wheel --no-deps --no-cache-dir --wheel-dir /wheels .

FROM python:3.12-slim@sha256:27f90d79cc85e9b7b2560063ef44fa0e9eaae7a7c3f5a9f74563065c5477cc24 AS test
WORKDIR /workspace
COPY pyproject.toml README.md ./
COPY src ./src
COPY tests ./tests
COPY quality ./quality
RUN pip install --no-cache-dir '.[dev]'
CMD ["sh", "-c", "pytest && ruff check . && python quality/check_score.py"]

FROM python:3.12-slim@sha256:27f90d79cc85e9b7b2560063ef44fa0e9eaae7a7c3f5a9f74563065c5477cc24 AS runtime
LABEL org.opencontainers.image.source="https://github.com/ndndndn1/flow-robot-bridge"
RUN groupadd --gid 10001 bridge && useradd --uid 10001 --gid bridge --no-create-home --shell /usr/sbin/nologin bridge
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels
USER 10001:10001
EXPOSE 8080
ENTRYPOINT ["flow-robot-bridge", "--host", "0.0.0.0", "--port", "8080"]
