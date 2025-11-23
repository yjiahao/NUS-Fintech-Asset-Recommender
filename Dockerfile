##
# Dockerfile
#

# Debian Linux
FROM python:3.12.1-slim-bookworm

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive POETRY_VERSION=2.1.3

# Create non-root user - regular users start with user ID 1000 (https://www.baeldung.com/linux/user-ids-reserved-values)
# Adapted from https://github.com/nodejs/docker-node/blob/main/22/bookworm-slim/Dockerfile
RUN groupadd --gid 1000 python \
    && useradd --uid 1000 --gid python --shell /bin/bash --create-home python

# Install system packages: cURL (used in healthcheck), dumb-init (used in Dockerfile),
# nano/vim (editor), git/OpenSSH (used for installing packages from private repositories),
# pipx (for installing Poetry)
RUN apt-get --yes update \
    && apt-get --yes --no-install-recommends install curl dumb-init nano pipx vim \
    && rm -rf /var/lib/apt/lists/*

# Install libraries for psycopg2 to work (instead of installing psycopg2-binary version)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc

# Switch to non-root user before installing Poetry else will have issues installing dependencies and running app
# All paths use /home/python explictly as $HOME and ~ do not seem to be resolved after switching user
# Need to set PATH env var (as ensurepath needs relogin) else can't run Poetry after installation via Pipx
USER python
ENV PATH="/home/python/.local/bin:$PATH"
# RUN pipx ensurepath \
#     && pipx install "poetry==$POETRY_VERSION" \
#     && poetry --version

RUN python3.12 -m pip install --upgrade pip setuptools \
    && python3.12 -m pip install "poetry==$POETRY_VERSION" \
    && poetry --version

# Create app directory and switch to it
RUN mkdir -p /home/python/app/log \
    && mkdir -p /home/python/app/src \
    && mkdir -p /home/python/app/tmp
WORKDIR /home/python/app

# Copy only essential files and folders, including client-specific custom code that may be bundled with application
# Docker recommends using COPY instruction over ADD.
# Placing the copy commands explicitly here is easier to troubleshoot
# than using .dockerignore. Do NOT copy .env inside here, use docker-compose.yml
# or Docker CLI to set environment variables for the container instead.
COPY --chown=python:python src/app/ /home/python/app/src/
# copy model file over
COPY --chown=python:python models/ /home/python/app/models/
COPY --chown=python:python .python-version poetry.lock pyproject.toml /home/python/app/

# Install production dependencies
# Config in poetry.toml ensures dependencies are created inside the app directory and that a new
# virtual environment is created as we will not be running as root (see
# https://www.reddit.com/r/learnpython/comments/13pq62l/comment/jlaya2d for more info)
RUN poetry config virtualenvs.create false
RUN pip install --no-cache-dir torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu
RUN poetry install --no-root

# Set "python" user as owner of app directory as the container will not be run as root
RUN chown -R python:python /home/python/app/

# expose gradio port
EXPOSE 7860
# get gradio to listen on all network interfaces
ENV GRADIO_SERVER_NAME='0.0.0.0'

# Using dumb-init allows proper terminating of application in Docker container
# CMD can be overridden via `command` in docker-compose.yml while ENTRYPOINT ensures CMD/command go thru dumb-init
# Run as non-root - see https://snyk.io/blog/10-best-practices-to-containerize-nodejs-web-applications-with-docker
ENTRYPOINT ["dumb-init", "--"]
CMD ["poetry", "run", "gradio", "src/app.py"]