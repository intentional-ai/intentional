# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Intent routing logic.
"""

from typing import Any, Dict
import logging

import networkx

from intentional_core.tools import Tool, ToolParameter, load_tools_from_dict


logger = logging.getLogger(__name__)


BACKTRACKING_CONNECTION = "_backtrack_"
START_CONNECTION = "_start_"
DEFAULT_PROMPT_TEMPLATE = """
{background}

Your goal is '{stage_name}': {current_goal}

You need to reach one of these situations:
{outcomes}
{transitions}

Talk to the user to reach one of these outcomes and once you do, classify the response with the {intent_router_tool} tool.
You MUST use one of the outcomes described above when invoking the {intent_router_tool} tool or it will fail.
Call the tool as soon as possible. Call it ONLY right after the user's response, before replying to the user. This will
help the system to understand the user's response and act accordingly. NEVER call this tool after another tool output.
You must say something to the user after each tool call!
Never call any tool, except for {intent_router_tool}, before telling something to the user! For example, if
you want to check what's the current time, first tell the user "Let me see the time", then invoke the tool, and then tell
them the time, such as "10:34 am". This will keep the user engaged in the conversation!
If the user just says something short, such as "ok", "hm hm", "I see", etc., you don't need to call the {intent_router_tool}
to classify this response. Ignore it and continue to work towards your goal.
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
        self.graph = networkx.MultiDiGraph()

        # Init the stages
        self.stages = {}
        for stage_name, stage_config in config["stages"].items():
            logger.debug("Loading stage %s", stage_name)
            self.stages[stage_name] = Stage(stage_config)
            self.graph.add_node(stage_name)

        # Connect the stages
        for stage_name, stage in self.stages.items():
            for outcome_name, outcome_config in stage.outcomes.items():
                if outcome_config["move_to"] not in [*self.stages, BACKTRACKING_CONNECTION]:
                    raise ValueError(
                        f"Stage {stage_name} has an outcome leading to an unknown stage {outcome_config['move_to']}"
                    )
                self.graph.add_edge(stage_name, outcome_config["move_to"], key=outcome_name)

        # Initial prompt
        initial_stage = ""
        for stage_name, stage in self.stages.items():
            if START_CONNECTION in stage.accessible_from:
                if initial_stage:
                    raise ValueError("Multiple start stages found!")
                initial_stage = stage_name
        if not initial_stage:
            raise ValueError("No start stage found!")

        self.current_stage_name = initial_stage
        self.backtracking_stack = []

    @property
    def current_stage(self):
        """
        Shorthand to get the current stage instance.
        """
        return self.stages[self.current_stage_name]

    async def run(self, params: Dict[str, Any]) -> str:
        """
        Given the response's classification, returns the new system prompt and the tools accessible in this stage.

        Args:
            params: The parameters for the tool. Contains the `response_type`.

        Returns:
            The new system prompt and the tools accessible in this stage.
        """
        if not params:
            # Initial prompt
            return self.get_prompt(), self.current_stage.tools

        selected_outcome = params["outcome"]
        transitions = self.get_transitions()

        if selected_outcome not in self.current_stage.outcomes and selected_outcome not in transitions:
            raise ValueError(f"Unknown outcome {params['outcome']}")

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
        outcomes = "\n".join(f"  - {name}: {data['description']}" for name, data in self.current_stage.outcomes.items())
        transitions = "\n".join(f"  - {stage}: {self.stages[stage].description}" for stage in self.get_transitions())
        return DEFAULT_PROMPT_TEMPLATE.format(
            intent_router_tool=self.name,
            stage_name=self.current_stage_name,
            background=self.background,
            current_goal=self.current_stage.goal,
            outcomes=outcomes,
            transitions=transitions,
        )

    def get_transitions(self):
        """
        Return a list of all the stages that can be reached from the current stage.
        """
        return [
            stage
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

    def __init__(self, config: Dict[str, Any]) -> None:
        self.goal = config["goal"]
        self.description = config.get("description", "--no description provided--")
        self.accessible_from = config.get("accessible_from", [])
        if isinstance(self.accessible_from, str):
            self.accessible_from = [self.accessible_from]
        self.tools = load_tools_from_dict(config.get("tools", {}))
        self.outcomes = config.get("outcomes", {})
