# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from intentional_core import IntentRouter


def test_router_must_have_stages():
    with pytest.raises(ValueError, match="The conversation must have at least one stage."):
        IntentRouter({})
    with pytest.raises(ValueError, match="The conversation must have at least one stage."):
        IntentRouter({"stages": {}})


def test_router_no_start_stage():
    with pytest.raises(ValueError, match="No start stage found!"):
        IntentRouter(
            {
                "stages": {
                    "ask_for_name": {
                        "goal": "Ask the user for their name",
                    },
                }
            }
        )


def test_router_many_start_stages():
    with pytest.raises(ValueError, match="Multiple start stages found!"):
        IntentRouter(
            {
                "stages": {
                    "ask_for_name": {
                        "accessible_from": ["_start_"],
                        "goal": "Ask the user for their name",
                    },
                    "ask_for_age": {
                        "accessible_from": ["_start_"],
                        "goal": "Ask the user for their age",
                    },
                }
            }
        )


def test_router_one_start_stage():
    intent_router = IntentRouter(
        {
            "stages": {
                "ask_for_name": {
                    "accessible_from": ["_start_"],
                    "goal": "Ask the user for their name",
                }
            }
        }
    )
    assert intent_router.initial_stage == "ask_for_name"
