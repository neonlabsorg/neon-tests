# syntax=docker/dockerfile:1.3

ARG OZ_TAG=latest
ARG DOCKER_HUB_ORG_NAME
FROM ${DOCKER_HUB_ORG_NAME}/openzeppelin-contracts:${OZ_TAG} as oz-contracts


FROM ubuntu:20.04

ARG DEBIAN_FRONTEND=noninteractive
ARG CONTRACTS_BRANCH
ARG DOCKER_HUB_ORG_NAME

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
    VIRTUAL_ENV="/.venv" \
    DOWNLOAD_PATH="/root/.cache/hardhat-nodejs/compilers-v2/linux-amd64" \
    REPOSITORY_PATH="https://binaries.soliditylang.org/linux-amd64" \
    SOLC_BINARY="solc-linux-amd64-v0.7.6+commit.7338295f"

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# ---- Install system dependencies using BuildKit caching ----
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        software-properties-common \
        python-dev \
        ca-certificates \
        curl \
        gnupg \
        git \
        build-essential \
        default-jdk \
        libxkbcommon0 \
        libxdamage1 \
        libgbm1 \
        libpango-1.0-0 \
        libcairo2 \
        xvfb && \
    # Prepare repo for node 18
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
        | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_18.x nodistro main" \
        | tee /etc/apt/sources.list.d/nodesource.list && \
    # Add deadsnakes PPA for Python 3.10
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        python3.10 \
        python3.10-distutils \
        nodejs && \
    # Clean up
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python3 python /usr/bin/python3.10 2 && \
    update-alternatives --install /usr/bin/python3 python /usr/bin/python3.8 1

RUN curl -Lo /tmp/allure.tgz \
      https://repo.maven.apache.org/maven2/io/qameta/allure/allure-commandline/2.21.0/allure-commandline-2.21.0.tgz && \
    tar -zxvf /tmp/allure.tgz -C /opt/ && \
    ln -s /opt/allure-2.21.0/bin/allure /usr/bin/allure && \
    rm /tmp/allure.tgz

# ---- Install Pip and create a virtual environment ----
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10 && \
    pip3 install uv && \
    uv venv

ENV PATH="${VIRTUAL_ENV}/bin:$PATH"

# ---- Copy only requirements first to leverage build cache ----
COPY ./deploy/requirements /opt/requirements

RUN --mount=type=cache,target=/root/.cache/pip \
    uv pip install -r /opt/requirements/click.txt

WORKDIR /opt/neon-tests
COPY . /opt/neon-tests

RUN --mount=type=cache,target=/root/.cache/pip \
    python3 ./clickfile.py requirements -d all

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

