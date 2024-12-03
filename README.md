# Intentional

Intentional is an open-source framework to build reliable, multimodal and multi-channel LLM chatbots that actually talk and behave as you expect.

NOTE: Intentional is still in its very early stages, and there are a lot of rough edges to it. To give any feedback or contribute, [get in touch](https://github.com/intentional-ai/intentional/issues/new)!

## Getting Started

First, install Intentional:

```
pip install intentional
```

**NOTE**: you may also need to install `portaudio` with `sudo apt install portaudio19-dev`.

Next, get a configuration file. For your first test run you should pick [this file](https://github.com/intentional-ai/intentional/blob/main/examples/example_cli_text_chat.yml), which needs no additional plugins, but you can find a few other examples [here](https://github.com/intentional-ai/intentional/tree/main/examples).

**NOTE**: The example here also requires an OpenAI key. Export it as an environment variable called `OPENAI_API_KEY` before proceeding.

Assuming your configuration file is called `intentional_bot.yml`, you can now launch your bot by doing:

```
intentional intentional_bot.yml
```

The output should look like:

```
==> Chat is ready!

User:
```

Type in your message and the bot is going to respond.

### Draw the conversation

To see the graph of the conversation defined by this configuration file, run:

```
intentional example.yml --draw
```

The graph will be saved next to your configuration file as `example.png`.

## Documentation

You can find all the documentation [here](https://intentional-ai.github.io/intentional/), including the API reference for the core packages and all the plugins hosted in this repository.

## License

All the content of this repository is distributed under the terms of the [AGPL](LICENSE) license. If that doesn't work for you, [get in touch](mailto:github@zansara.dev).
