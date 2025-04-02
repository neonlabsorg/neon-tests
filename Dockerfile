ARG DOCKER_HUB_ORG_NAME
ARG BASE_IMAGE_TAG
FROM ${DOCKER_HUB_ORG_NAME}/neon_tests_base:${BASE_IMAGE_TAG} AS base_image

FROM ubuntu:20.04
COPY --from=base_image  /opt/neon-tests /opt/neon-tests

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
    PATH="/.venv/bin:$PATH"

# Set timezone and install only the necessary packages in a single layer
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    apt update && \
    apt upgrade -y && \
    apt install default-jdk curl -y && \
    curl -o allure-2.21.0.tgz -Ls https://repo.maven.apache.org/maven2/io/qameta/allure/allure-commandline/2.21.0/allure-commandline-2.21.0.tgz && \
    tar -zxvf allure-2.21.0.tgz -C /opt/  && \
    ln -s /opt/allure-2.21.0/bin/allure /usr/bin/allure && \
    rm allure-2.21.0.tgz && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN apt update && \
    apt upgrade -y && apt install -y libxkbcommon0 \
    libxdamage1 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    xvfb

# Copy application from builder stage
WORKDIR /opt/neon-tests
