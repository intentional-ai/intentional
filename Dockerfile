# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12.8

FROM python:${PYTHON_VERSION}-slim AS base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1
# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy the source code into the container.
COPY ./intentional/ ./intentional/
COPY ./intentional-core/ ./intentional-core/
# --> You can limit this to the plugins you actually need
COPY ./plugins/ ./

# --> Copy the config file in the container
COPY ./examples/fastapi_text_chat.yml ./config.yml

# Install Intentional and plugins
RUN apt update
RUN apt install -y gcc portaudio19-dev
RUN python -m pip install uv
RUN python -m uv pip install --system intentional-core/
# --> Add the necessary plugins here
RUN python -m uv pip install --system intentional-openai/ intentional-fastapi/
RUN python -m uv pip install --system intentional/

# Expose the port that the application listens on.
EXPOSE 8000

# Run Intentional
# --> Set the config file here
CMD ["intentional", "config.yml"]
