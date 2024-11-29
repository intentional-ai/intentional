
## The configuration file

The configuration file is the core of Intentional bots. They are YAML files that define a conversation such as the one we've seen above.

Here is an example of a conversation file. Don't feel overwhelmed just yet! Each part will be explained separately.

```yaml
bot:
  type: text_chat
  llm:
    client: openai
    name: gpt-4o
interface: textual_ui
modality: text_messages

plugins:
- intentional_textual_ui
- intentional_openai

conversation:
  background: "You're Jane, an interviewer calling a person to collect some data about them."
  stages:
    ask_for_name:
      goal: ask the user for their name.
      outcomes:
        name_given:
          description: user tells you their name
          move_to: ask_for_age
        user_refuses:
          description: user stated clearly they don't want to tell you their name
          move_to: bye

    ask_for_age:
      goal: ask the user for their age.
      outcomes:
        age_given:
          description: user tells you their age
          move_to: ask_for_city
        user_refuses:
          description: user stated clearly they don't want to tell you their age
          move_to: bye

    ask_for_address:
      goal: ask the user for their current address.
      outcomes:
        address_given:
          description: user tells you their current address and the address exists.
          move_to: confirm_data
        user_refuses:
          description: user stated clearly they don't want to tell you their current address
          move_to: bye
      tools:
        - address_exists

    confirm_data:
      goal: Repeat the user's name, age and address you have gathered and ask them to confirm that everything is correct.
      outcomes:
        user_confirms:
          description: user confirms everything you said is correct.
          move_to: bye
        user_refuses:
          description: user stated clearly they won't say if the data you gathered is correct or not.
          move_to: bye
        mistakes_found:
          description: user states that there are mistakes in the data you repeated.
          move_to: amend_data

    amend_data:
      goal: ask the user which information they want to correct and ask them to provide the correct information. If they already provided it while asking you to correct said data, repeat it to them and ask them to confirm it.
      outcomes:
        correct_data_given:
          description: user provides the correct information
          move_to: confirm
        user_refuses:
          description: user stated clearly they won't confirm the data is now correct or not.
          move_to: bye

    bye:
      goal: thank the user for their time and say goodbye to them.
      outcomes:
        ok:
          description: user says goodbye too
          move_to: _end_

    questions:
      accessible_from: _all_
      description: the user asks you something about yourself, your task, or why you're calling them and collecting this data about them.
      goal: answer all of the user's question regarding yourself, your task, and why you're calling them and collecting this data about them. After you answer, always ask the user if they have any more question for you.
      outcomes:
        no_more_questions:
          description: the user has no more questions.
          move_to: _backtrack_
      tools:
       - knowledge_base
```
### Bot configuration

```yaml
bot:
  type: text_chat
  llm:
    client: openai
    name: gpt-4o
interface: textual_ui
modality: text_messages
```

Intentional supports several styles of bots, so the configuration file must first of all specify what sort of bot we're building. The `bot` section takes care of this definition.

#### Bot type

First, we need to specify the `type`. Right now Intentional supports a few types of bots:

- `text chat`: the bot and the user take turns exchanging text messages, as in a regular chat application. To each single message of the user the bot will respond with one or more messages.

- `audio/text`: the bot and the user each communicate by audio. They may either take turns explicitly (such as in a chat conversation where both parties exchange audio messages) or they may both talk continuously and be able to interrupt each other. The audio messages are converted to text and vice-versa, to make text-only LLMs able to be used for voice conversations.

- `websocket`: the bot and the user each communicate by publishing audio messages on a websocket continuously, without taking turns. There is no transcription to text happening within Intentional. This modality mirrors how OpenAI's Realtime API works.

!!! note

    More documentation on the `type` field coming soon!

#### LLM

Next, we need to specify what LLM we want to use. The `llm` field takes two parameters:

- `client`: which client to use to connect to the LLM. For example, `openai` (provided by the `intentional-openai` plugin, see below) will tell Intentional to use the OpenAI SDK to connect to the LLM.

- `name`: the name of the LLM (if required by the specified client). In this case, we specify `gpt-4o`.

If the client you specified requires any other parameters, they can be listed in this section.

#### Interface

`interface` makes you configure the user interface the bot will use to communicate. If you want the bot to show its replies in the commend line, use `interface: terminal`. Do you prefer to use a chat application? Intentional can spin up a Telegram bot for you if you specify `interface: telegram`. Need a FastAPI endpoint? `interface: fastapi`. And so on.

!!! note

    Interfaces are always provided by a plugin: Intentional comes with no interfaces by default. Make sure to install the plugins you need.

    You can find a list of available plugins in the API Reference sidebar. Better documentation of the available plugins is coming soon.

#### Modality

Last, let's specify the `modality`. The modality is the medium the bot uses to communicate with the user, such as text messages, audio messages, audio stream, even video stream (not supported yet).

Some bot interfaces support more than one modality, so we need to specify what our bot is supposed to use as its primary modality.

Right now, most bots support either one of these modalities:

- `text_messages`: classic chat-style messages.
- `audio_stream`: telephone-like interaction where bot and user freely talk together.

### Plugins

```yaml
plugins:
- intentional_textual_ui
- intentional_openai
```

Intentional is highly modular, and some of the parameters highlighted above require their own plugins. You can specify which plugins your bot needs by listing them in this section.

In our example we're using OpenAI as the LLM provider and Textual UI as our UI. Therefore we can list these two plugins to make sure Intentional loads them properly.

!!! note

    If this section is not specified, Intentional will search your virtual environment for any package that begins with `intentional_` and will try to import it. In many cases this may be sufficient.

### Conversation

```yaml
conversation:
  background: "You're Jane, an interviewer calling a person to collect some data about them."
  stages:
```

The conversation block is where we define all the stages and the transitions among them. Together with the `stages` field, which is where all the definition of the stages will go, you can also define a `background` field that includes some basic information about the bot's personality and overall goal.

!!! note

    Avoid using the `background` field to describe the bot's goal in a specific way. Giving the bot too much information about its goals will make it more likely to hallucinate questions and improvise transitions between stages!

    You should use the `background` field to specify the bot's personality, a few very basic information about itself, and the context the bot will be in (such as whether they're calling over the phone, having a text chat, etc)

### Stages

```yaml
ask_for_address:
    goal: ask the user for their current address.
    outcomes:
        address_given:
            description: user tells you their current address and the address exists.
            move_to: confirm_data
        user_refuses:
            description: user stated clearly they don't want to tell you their current address
            move_to: bye
        tools:
        - address_exists
```

This is the basic structure of a stage.

Stages have a **name**, such as `ask_for_address`, which will be shown in the diagram of a conversation such as the ones above.

Stages have a **`goal`** field: here you should describe the goal the bot must pursue while it's in this stage. For example, when the bot is in the `ask_for_address` stage, its goal is to `ask the user for their current address`. This makes sure that the bot does what you expect it to.

Stages have **`outcomes`**: each of these outcomes is named, such as `address_given`.
Each outcome has two properties:

- a **`description`**, like `user tells you their current address and the address exists.`, that the bot will use to check whether this outcome has been accomplished or not.

- a **`move_to`** field, that points to the next stage the bot should move to once this outcome is reached. For example, if the `address_given` outcome has been reached, the bot should move on to `confirm_data`.

Stages also have a list of **`tools`** that they should have access to. For example, `ask_for_address` needs access to the `address_exists` tool. The tool itself will contain all the information needed for the bot to use it, but if further configuration is required, it can be listed under the tool as well.

!!! note

    Listing the tools by name is sufficient for the bot to find them, but they must have been imported by the Python process running your bot in order to be found. See more in the Tools section of the docs.

There are a few more fields that may be used to define stages outside of the main conversation flow, such as the `questions` stage:

```yaml
    questions:
      accessible_from: _all_
      description: the user asks you something about yourself, your task, or why you're calling them and collecting this data about them.
      goal: answer all of the user's question regarding yourself, your task, and why you're calling them and collecting this data about them. After you answer, always ask the user if they have any more question for you.
      outcomes:
        no_more_questions:
          description: the user has no more questions.
          move_to: _backtrack_
      tools:
       - knowledge_base
```

This stage has two additional fields:

- **`accessible_from`** lets you specify from which stages the bot should be able to jump here in case of need. It can take a few values:
    - `_all_` means that this stage is accessible by all other stages.
    - a list of stages: in this case, the bot will only be able to jump here from one of the stages listed and nowhere else.

- **`description`**: much like the `description` field of outcomes, this field describes when the bot should leave the stage it find itself in and jump here instead.

Outcomes as well are different in this stage. The `move_to` field is set to **`_backtrack_`**, which tells the bot that once this outcome is reached, the bot should jump back to whatever stage it was in before landing here. For example, if the user asked the question "Why do you need my address"? in the `ask_for_address` stage, once the bot replied and the user is happy with its response, the `_backtrack_` field tells the bot to jump back to where it was before, which is `ask_for_address`.
