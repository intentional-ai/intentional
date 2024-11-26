# Intentional

Intentional is an open-source Python framework to build reliable LLM chatbots that actually talk and behave as you expect.

Pure LLM-based chatbots are very hard to control: when a lot of very specific instructions are pushed into their system prompt, their performance will get worse and worse the more instructions you add. These bots will work very well on small demos, but don’t scale to real use cases, where you may need the bot to follow a very specific set of workflows depending on the situation it find itself in, without improvising.

Intentional introduces a new way of prompting the LLM in a way that gives the developer full control on the conversation at scale while retaining the smooth conversational skills of the LLM.

## Features

Intentional lets you contro the way your chatbot behaves by specifying a **conversation graph** made of several **stages**.

At each stage, the LLM has a very specific **goal** to accomplish and will stick to it until it reaches one of the **outcomes** you specify. Once the LLM is confident that one of the outcomes is reached, it will move over to the next stage and continue along the conversation graph in this way.

For example, here is an example of a very simple conversation graph:

```TODO

```
