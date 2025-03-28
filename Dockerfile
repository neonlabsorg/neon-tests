
ARG OZ_TAG=latest
ARG DOCKER_HUB_ORG_NAME=neonlabsorg
FROM ${DOCKER_HUB_ORG_NAME}/openzeppelin-contracts:${OZ_TAG} AS oz-contracts

FROM ghcr.io/astral-sh/uv:python3.10-bookworm-slim AS builder

ENV UV_LINK_MODE=copy

ARG DEBIAN_FRONTEND=noninteractive
ARG CONTRACTS_BRANCH=develop
ARG DOCKER_HUB_ORG_NAME=neonlabsorg
ENV VIRTUAL_ENV="/.venv" \
    DOWNLOAD_PATH="/root/.cache/hardhat-nodejs/compilers-v2/linux-amd64" \
    REPOSITORY_PATH="https://binaries.soliditylang.org/linux-amd64" \
    SOLC_BINARY="solc-linux-amd64-v0.7.6+commit.7338295f"

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        software-properties-common \
        ca-certificates \
        curl \
        gnupg \
        git \
        build-essential && \
    # Prepare repo for node 18
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
        | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_18.x nodistro main" \
        | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        nodejs && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

WORKDIR /opt/neon-tests
COPY . /opt/neon-tests

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-editable

ENV PATH="/.venv/bin:$PATH"

ENV DOCKER_HUB_ORG_NAME=${DOCKER_HUB_ORG_NAME}
RUN python3 ./clickfile.py update-contracts --branch ${CONTRACTS_BRANCH}

# Replace openzeppelin-contracts from Stage 1
RUN rm -rf /opt/neon-tests/compatibility/openzeppelin-contracts
COPY --from=oz-contracts /usr/src/app /opt/neon-tests/compatibility/openzeppelin-contracts
COPY --from=oz-contracts /root/.cache/hardhat-nodejs /root/.cache/hardhat-nodejs

RUN cd compatibility/openzeppelin-contracts && docker/compile_contracts.sh

RUN mkdir -p ${DOWNLOAD_PATH} && \
    curl -o ${DOWNLOAD_PATH}/${SOLC_BINARY} ${REPOSITORY_PATH}/${SOLC_BINARY} && \
    curl -o ${DOWNLOAD_PATH}/list.json ${REPOSITORY_PATH}/list.json && \
    chmod -R 755 ${DOWNLOAD_PATH}


FROM python:3.10-slim-bookworm AS final
COPY --from=builder /opt/neon-tests /opt/neon-tests

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
    REQUEST_AMOUNT=20000\
    PATH="/.venv/bin:$PATH"

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt update && \
    apt upgrade -y && \
    apt install default-jdk curl -y && \
    curl -o allure-2.21.0.tgz -Ls https://repo.maven.apache.org/maven2/io/qameta/allure/allure-commandline/2.21.0/allure-commandline-2.21.0.tgz && \
    tar -zxvf allure-2.21.0.tgz -C /opt/  && \
    ln -s /opt/allure-2.21.0/bin/allure /usr/bin/allure

