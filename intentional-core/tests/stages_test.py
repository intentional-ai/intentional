# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later

import re
import pytest
from intentional_core.intent_routing import Stage


def test_stage_with_custom_template_needs_nothing_else():
    Stage("ask_for_name", {"custom_template": "Hello!"})


def test_stage_must_have_goal():
    with pytest.raises(ValueError, match="Stage 'ask_for_name' is missing a goal"):
        Stage("ask_for_name", {"outcomes": {}})


def test_start_stages_are_not_external_stages():
    assert Stage(
        "ask_for_name",
        {
            "accessible_from": ["_start_"],
            "goal": "Ask the user for their name",
        },
    )


def test_external_stage_must_have_description():
    with pytest.raises(
        ValueError,
        match=re.escape(
            "Stages that set the 'accessible_from' field also need a description. "
            "'ask_for_name' has 'accessible_from' set to ['_all_'], but no 'description' field."
        ),
    ):
        Stage(
            "ask_for_name",
            {
                "accessible_from": ["_all_"],
                "goal": "Ask the user for their name",
            },
        )


def test_stage_outcomes_need_a_description():
    with pytest.raises(
        ValueError,
        match="Outcome 'name_given' in stage 'ask_for_name' is missing a description",
    ):
        Stage(
            "ask_for_name",
            {
                "accessible_from": ["_start_"],
                "goal": "Ask the user for their name",
                "outcomes": {
                    "name_given": {
                        "move_to": "ask_for_age",
                    }
                },
            },
        )


def test_stage_outcomes_need_a_move_to():
    with pytest.raises(
        ValueError,
        match="Outcome 'name_given' in stage 'ask_for_name' is missing a 'move_to' field",
    ):
        Stage(
            "ask_for_name",
            {
                "accessible_from": ["_start_"],
                "goal": "Ask the user for their name",
                "outcomes": {
                    "name_given": {
                        "description": "The user provided their name",
                    }
                },
            },
        )
