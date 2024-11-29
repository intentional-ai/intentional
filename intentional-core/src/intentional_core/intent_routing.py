# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Intent routing logic.
"""

from typing import Any, Dict, Optional

import structlog
import networkx

from intentional_core.tools import Tool, ToolParameter, load_tools_from_dict
from intentional_core.end_conversation import EndConversationTool


log = structlog.get_logger(logger_name=__name__)


BACKTRACKING_CONNECTION = "_backtrack_"
START_CONNECTION = "_start_"
DEFAULT_PROMPT_TEMPLATE = """
{background}

Your goal is '{stage_name}': {current_goal}

{outcomes}
{transitions}

Talk to the user to reach one of these outcomes and once you do, classify the response with the '{intent_router_tool}' tool.
You MUST use one of the outcomes described above when invoking the '{intent_router_tool}' tool or it will fail.
Call the tool as soon as possible, but make sure to talk to the user first if your goal description says so.
Call it ONLY right after the user's response, before replying to the user. This will help the system to understand the
user's response and act accordingly. NEVER call this tool after another tool output.
You must say something to the user before each tool call!
Never call any tool, except for '{intent_router_tool}', before telling something to the user! For example, if
you want to check what's the current time, first tell the user "Let me see the time", then invoke the tool, and then tell
them the time, such as "10:34 am". This will keep the user engaged in the conversation!
If the user just says something short, such as "ok", "hm hm", "I see", etc., you don't need to call the '{intent_router_tool}'
to classify this response unless that's all you need to proceed. Ignore it and continue to work towards your goal.
Never do ANYTHING ELSE than what the goal describes! This is very important!
"""


class IntentRouter(Tool):
    """
    Special tool used to alter the system prompt depending on the user's response.
    """

    name = "classify_response"
    description = "Classify the user's response for later use."
    parameters = [
        ToolParameter(
            "outcome",
            "The outcome the conversation reached, among the ones described in the prompt.",
            "string",
            True,
            None,
        ),
    ]

    def __init__(self, config: Dict[str, Any]) -> None:
        self.background = config.get("background", "You're a helpful assistant.")
        self.initial_message = config.get("initial_message", None)
        self.graph = networkx.MultiDiGraph()

        # Init the stages
        self.stages = {}
        if "stages" not in config or not config["stages"]:
            raise ValueError("The conversation must have at least one stage.")
        for name, stage_config in config["stages"].items():
            log.debug("Adding stage", stage_name=name)
            self.stages[name] = Stage(name, stage_config)
            self.stages[name].tools[self.name] = self  # Add the intent router to the tools list of each stage
            self.graph.add_node(name)

        # Add end stage
        name = "_end_"
        log.debug("Adding stage", stage_name=name)
        end_tool = EndConversationTool(intent_router=self)
        self.stages[name] = Stage(
            name,
            {"custom_template": f"The conversation is over. Call the '{end_tool.name}' tool."},
        )
        self.stages[name].tools[end_tool.name] = end_tool
        self.graph.add_node("_end_")

        # Connect the stages
        for name, stage in self.stages.items():
            for outcome_name, outcome_config in stage.outcomes.items():
                if outcome_config["move_to"] not in [
                    *self.stages,
                    BACKTRACKING_CONNECTION,
                ]:
                    raise ValueError(
                        f"Stage '{name}' has an outcome leading to an unknown stage '{outcome_config['move_to']}'"
                    )
                log.debug(
                    "Adding connection",
                    origin=name,
                    target=outcome_config["move_to"],
                    outcome=outcome_name,
                )
                self.graph.add_edge(name, outcome_config["move_to"], key=outcome_name)

        # Find initial stage
        self.initial_stage = ""
        for name, stage in self.stages.items():
            if START_CONNECTION in stage.accessible_from:
                if self.initial_stage:
                    raise ValueError("Multiple start stages found!")
                log.debug("Found start stage", stage_name=name)
                self.initial_stage = name
        if not self.initial_stage:
            raise ValueError("No start stage found!")

        self.current_stage_name = self.initial_stage
        self.backtracking_stack = []

    @property
    def current_stage(self):
        """
        Shorthand to get the current stage instance.
        """
        return self.stages[self.current_stage_name]

    async def run(self, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Given the response's classification, returns the new system prompt and the tools accessible in this stage.

        Args:
            params: The parameters for the tool. Contains the `response_type`.

        Returns:
            The new system prompt and the tools accessible in this stage.
        """
        selected_outcome = params["outcome"]
        transitions = self.get_external_transitions()

        if selected_outcome not in self.current_stage.outcomes and selected_outcome not in transitions:
            raise ValueError(f"Unknown outcome '{params['outcome']}' for stage '{self.current_stage_name}'")

        if selected_outcome in self.current_stage.outcomes:
            next_stage = self.current_stage.outcomes[params["outcome"]]["move_to"]

            if next_stage != BACKTRACKING_CONNECTION:
                # Direct stage to stage connection
                self.current_stage_name = next_stage
            else:
                # Backtracking connection
                self.current_stage_name = self.backtracking_stack.pop()
        else:
            # Indirect transition, needs to be tracked in the stack
            self.backtracking_stack.append(self.current_stage_name)
            self.current_stage_name = selected_outcome

        return self.get_prompt(), self.current_stage.tools

    def get_prompt(self):
        """
        Get the prompt for the current stage.
        """
        outcomes = "You need to reach one of these situations:\n" + "\n".join(
            f"  - {name}: {data['description']}" for name, data in self.current_stage.outcomes.items()
        )
        transitions = "\n".join(
            f"  - {stage}: {self.stages[stage].description}" for stage in self.get_external_transitions()
        )
        template = self.current_stage.custom_template or DEFAULT_PROMPT_TEMPLATE
        return template.format(
            intent_router_tool=self.name,
            stage_name=self.current_stage_name,
            background=self.background,
            current_goal=self.current_stage.goal,
            outcomes=outcomes,
            transitions=transitions,
        )

    def get_external_transitions(self):
        """
        Return a list of all the stages that can be reached from the current stage that are not direct connections.
        """
        return [
            name
            for name, stage in self.stages.items()
            if (
                (self.current_stage_name in stage.accessible_from or "_all_" in stage.accessible_from)
                and name != self.current_stage_name
            )
        ]


class Stage:
    """
    Describes a stage in the bot's conversation.
    """

    def __init__(self, stage_name, config: Dict[str, Any]) -> None:
        self.custom_template = config.get("custom_template", None)
        self.goal = config.get("goal", None)
        self.description = config.get("description", None)
        self.accessible_from = config.get("accessible_from", [])
        if isinstance(self.accessible_from, str):
            self.accessible_from = [self.accessible_from]
        self.tools = load_tools_from_dict(config.get("tools", {}))
        self.outcomes = config.get("outcomes", {})

        # If a custom template is given, nothing else is strictly needed
        if not self.custom_template:
            # Make sure the stage has a goal
            if not self.goal:
                raise ValueError(f"Stage '{stage_name}' is missing a goal.")
            # If the stage is accessible from somewhere else than a direct transition, it needs a description
            if self.accessible_from and self.accessible_from != ["_start_"] and not self.description:
                raise ValueError(
                    "Stages that set the 'accessible_from' field also need a description. "
                    f"'{stage_name}' has 'accessible_from' set to {self.accessible_from}, but no 'description' field."
                )
        # Make sure all outcomes have a description
        for name, outcome in self.outcomes.items():
            if "description" not in outcome:
                raise ValueError(f"Outcome '{name}' in stage '{stage_name}' is missing a description.")
            if "move_to" not in outcome:
                raise ValueError(f"Outcome '{name}' in stage '{stage_name}' is missing a 'move_to' field.")

        log.debug(
            "Stage loaded",
            custom_template=self.custom_template,
            stage_goal=self.goal,
            stage_description=self.description,
            stage_accessible_from=self.accessible_from,
            stage_tools=self.tools,
            outcomes=self.outcomes,
        )
