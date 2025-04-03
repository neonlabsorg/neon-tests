ARG DOCKER_HUB_ORG_NAME
ARG BASE_IMAGE_TAG
FROM ${DOCKER_HUB_ORG_NAME}/neon_tests_base:${BASE_IMAGE_TAG} as base_image

FROM ghcr.io/astral-sh/uv:python3.10-bookworm-slim

WORKDIR /opt/neon-tests
ADD ./ /opt/neon-tests

COPY --from=base_image /opt/neon-tests/.venv /opt/neon-tests/.venv
COPY --from=base_image /opt/neon-tests/contracts/external/ /opt/neon-tests/contracts/external/
COPY --from=base_image /opt/neon-tests/compatibility/openzeppelin-contracts /opt/neon-tests/compatibility/openzeppelin-contracts
COPY --from=base_image /root/.cache/hardhat-nodejs  /root/.cache/hardhat-nodejs

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

# Combine all package installations into a single layer
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
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
