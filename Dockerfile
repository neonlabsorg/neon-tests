# syntax=docker/dockerfile:1.4

ARG DOCKER_HUB_ORG_NAME
ARG BASE_IMAGE_TAG
FROM ${DOCKER_HUB_ORG_NAME}/neon_tests_base:${BASE_IMAGE_TAG} as base_image

FROM ghcr.io/astral-sh/uv:python3.10-bookworm-slim

WORKDIR /opt/neon-tests

ENV TZ=Europe/Moscow \
    NETWORK_NAME="full_test_suite" \
    PROXY_URL="" \
    NETWORK_ID="" \
    FAUCET_URL="" \
    SOLANA_URL="" \
    FTS_JOBS_NUMBER=8 \
    FTS_USERS_NUMBER=15 \
    DUMP_ENVS=True \
    REQUEST_AMOUNT=20000 \
    PATH=".venv/bin:$PATH"

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y \
    default-jdk \
    curl \
    libxkbcommon0 \
    libxdamage1 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    xvfb && \
    curl -o allure-2.21.0.tgz -Ls https://repo.maven.apache.org/maven2/io/qameta/allure/allure-commandline/2.21.0/allure-commandline-2.21.0.tgz && \
    tar -zxvf allure-2.21.0.tgz -C /opt/ && \
    ln -s /opt/allure-2.21.0/bin/allure /usr/bin/allure && \
    rm allure-2.21.0.tgz && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy files from base image first (more likely to be cached across builds)
COPY --from=base_image /opt/neon-tests/.venv /opt/neon-tests/.venv
COPY --from=base_image /opt/neon-tests/contracts/external/ /opt/neon-tests/contracts/external/
COPY --from=base_image /opt/neon-tests/compatibility/openzeppelin-contracts /opt/neon-tests/compatibility/openzeppelin-contracts
COPY --from=base_image /root/.cache/hardhat-nodejs /root/.cache/hardhat-nodejs

# Add source code last as it's most likely to change
ADD ./ /opt/neon-tests
