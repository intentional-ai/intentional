# Intentional

Intentional is an open-source framework to build reliable LLM chatbots that actually talk and behave as you expect.

NOTE: Intentional is still in its very early stages, and there are a lot of rough edges to it. To give any feedback or contribute, [get in touch](https://github.com/intentional-ai/intentional/issues/new)!

## Installation

To get started, install Intentional with:

```
pip install intentional
```

This command will also install a simple CLI tool that lets you start out bots from a configuration file directly.

For example, to run the Textual UI example for a text-based chatbot, download [this example configuration file](https://github.com/intentional-ai/intentional/blob/main/examples/example_textualui_text_chat.yml) into a file called `example.yml`, make sure to install all the necessary plugins (`pip install intentional-textual-ui intentional-text-chat intentional-openai`) and then run:

```
intentional example.yml
```

If you installed Intentional by cloning the git repo, this and many more examples can be found under the `examples/` folder.

To see the graph of the conversation defined by this configuration file, run:

```
intentional example.yml --draw
```

The graph will be saved next to your configuration file as `example.png`.

## Documentation

You can find all the documentation [here](https://intentional-ai.github.io/intentional/), including the API reference for the core packages and all the plugins hosted in this repository.

-----

## License

All the content of this repository is distributed under the terms of the [AGPL](LICENSE) license.
