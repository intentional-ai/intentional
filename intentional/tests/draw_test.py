# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from intentional_core import IntentRouter


@pytest.mark.parametrize(
    "test_configs",
    [
        IntentRouter(
            {
                "stages": {
                    "ask_for_name": {
                        "accessible_from": ["_start_"],
                        "goal": "Ask the user for their name",
                        "outcomes": {
                            "success": {
                                "description": "The user says their name",
                                "move_to": "ask_for_age",
                            },
                            "failure": {
                                "description": "The user states clearly they're not going to share their name",
                                "move_to": "_end_",
                            },
                        },
                    },
                    "ask_for_age": {
                        "goal": "Ask the user for their age",
                        "outcomes": {
                            "success": {
                                "description": "The user says their age",
                                "move_to": "_end_",
                            },
                            "failure": {
                                "description": "The user states clearly they're not going to share their age",
                                "move_to": "_end_",
                            },
                        },
                    },
                }
            }
        )
    ],
)
def test_draw(test_configs):
    pass
