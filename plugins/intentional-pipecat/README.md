# Intentional - Pipecat

[![Made for Intentional](https://img.shields.io/badge/made_for-intentional-blue)](https://intentional-ai.github.io/intentional/docs/home/)
[![PyPI - Version](https://img.shields.io/pypi/v/intentional-pipecat.svg)](https://pypi.org/project/intentional-pipecat)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/intentional-pipecat.svg)](https://pypi.org/project/intentional-pipecat)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/intentional-pipecat)](https://pypistats.org/packages/intentional-pipecat)
[![Copier](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border-orange.json)](https://github.com/copier-org/copier)

Plugin that lets you build transcribed audio voice bots using Pipecat.

-----

## Table of Contents

- [Installation](#installation)
- [License](#license)

## Installation

You can install `intentional-pipecat` without extras:

```console
pip install intentional-pipecat[silero,deepgram,openai]
```

However, it will be unusable as-is, because it will come with nearly no dependencies.

In order to have any of the underlying dependencies installed (such as Silero's VAD, Deepgram, OpenAI, etc...) you must specify them as extras, like:

```console
pip install intentional-pipecat[silero,deepgram,openai]
```

For a list of all the available extras, see Pipecat's documentation or [their `pyproject.toml` file](https://github.com/pipecat-ai/pipecat/blob/main/pyproject.toml). We are going to try to keep this list up-to-date on Intentional's end, but in case of issues you can also install those dependencies by hand by doing:

```console
pip install pipecat-ai[<the extras you want>]
```

This guarantees that you get the correct extras for your version of Pipecat. Please open an issue if you find any discrepancies.

## Usage

In order to use Pipecat, you need to specify which components you want to use in the configuration file. For example:

```yaml
bot:
  type: pipecat
  llm:
    client: openai
    name: gpt-4o
  vad:
    module: silero
    client: SileroVADAnalyzer
  stt:
    module: deepgram
    client: DeepgramSTTService
  tts:
    module: azure
    client: AzureTTSService
```

This example would require the extras `silero`, `deepgram` and `azure`:

```console
pip install intentional-pipecat[silero,deepgram,azure]
```

See [Pipecat's documentation](https://docs.pipecat.ai/getting-started/overview) for more information about what modules and classes are available for the various pipeline components.

At this time, the Pipeline structure itself cannot be configured. [Open an issue](https://github.com/intentional-ai/intentional/issues/new) if you'd like to allow some degree of pipeline customization.

## License

`intentional` is distributed under the terms of the [AGPL](LICENSE.txt) license. If that doesn't work for you, [get in touch](mailto:github@zansara.dev).
