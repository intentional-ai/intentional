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


def test_router_graph_one_stage_disconnected_from_end():
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
    assert set(intent_router.graph.nodes) == {"ask_for_name", "_end_"}
    assert not set(intent_router.graph.edges)


def test_router_graph_one_stage_connected_to_end():
    intent_router = IntentRouter(
        {
            "stages": {
                "ask_for_name": {
                    "accessible_from": ["_start_"],
                    "goal": "Ask the user for their name",
                    "outcomes": {
                        "name_given": {
                            "description": "The user has given their name",
                            "move_to": "_end_",
                        }
                    },
                }
            }
        }
    )
    assert set(intent_router.graph.nodes) == {"ask_for_name", "_end_"}
    assert set(intent_router.graph.edges) == {("ask_for_name", "_end_", "name_given")}


def test_router_graph_two_connected_stages():
    intent_router = IntentRouter(
        {
            "stages": {
                "ask_for_name": {
                    "accessible_from": ["_start_"],
                    "goal": "Ask the user for their name",
                    "outcomes": {
                        "name_given": {
                            "description": "The user has given their name",
                            "move_to": "ask_for_age",
                        }
                    },
                },
                "ask_for_age": {
                    "goal": "Ask the user for their age",
                },
            }
        }
    )
    assert set(intent_router.graph.nodes) == {"ask_for_name", "ask_for_age", "_end_"}
    assert set(intent_router.graph.edges) == {("ask_for_name", "ask_for_age", "name_given")}


def test_router_transition_to_unknown_stage():
    with pytest.raises(
        ValueError,
        match="Stage 'ask_for_name' has an outcome leading to an unknown stage 'ask_for_age'",
    ):
        IntentRouter(
            {
                "stages": {
                    "ask_for_name": {
                        "accessible_from": ["_start_"],
                        "goal": "Ask the user for their name",
                        "outcomes": {
                            "name_given": {
                                "description": "The user has given their name",
                                "move_to": "ask_for_age",
                            }
                        },
                    }
                }
            }
        )


def test_router_backtrack_is_valid_transition():
    assert IntentRouter(
        {
            "stages": {
                "ask_for_name": {
                    "accessible_from": ["_start_"],
                    "goal": "Ask the user for their name",
                    "outcomes": {
                        "name_given": {
                            "description": "The user has given their name",
                            "move_to": "_backtrack_",
                        }
                    },
                }
            }
        }
    )


@pytest.mark.asyncio
async def test_router_direct_transition():
    router = IntentRouter(
        {
            "stages": {
                "ask_for_name": {
                    "accessible_from": ["_start_"],
                    "goal": "Ask the user for their name",
                    "outcomes": {
                        "name_given": {
                            "description": "The user has given their name",
                            "move_to": "ask_for_age",
                        }
                    },
                },
                "ask_for_age": {
                    "goal": "Ask the user for their age",
                    "outcomes": {
                        "age_given": {
                            "description": "The user has given their age",
                            "move_to": "_end_",
                        }
                    },
                },
            }
        }
    )
    assert router.get_external_transitions() == []
    _, _ = await router.run({"outcome": "name_given"})
    assert router.current_stage_name == "ask_for_age"


@pytest.mark.asyncio
async def test_router_wrong_transition():
    router = IntentRouter(
        {
            "stages": {
                "ask_for_name": {
                    "accessible_from": ["_start_"],
                    "goal": "Ask the user for their name",
                    "outcomes": {
                        "name_given": {
                            "description": "The user has given their name",
                            "move_to": "ask_for_age",
                        }
                    },
                },
                "ask_for_age": {
                    "goal": "Ask the user for their age",
                    "outcomes": {
                        "age_given": {
                            "description": "The user has given their age",
                            "move_to": "_end_",
                        }
                    },
                },
            }
        }
    )

    with pytest.raises(ValueError, match="Unknown outcome 'not_existing' for stage 'ask_for_name'"):
        _, _ = await router.run({"outcome": "not_existing"})


@pytest.mark.asyncio
async def test_router_direct_transition_to_end():
    router = IntentRouter(
        {
            "stages": {
                "ask_for_name": {
                    "accessible_from": ["_start_"],
                    "goal": "Ask the user for their name",
                    "outcomes": {
                        "name_given": {
                            "description": "The user has given their name",
                            "move_to": "_end_",
                        }
                    },
                }
            }
        }
    )
    assert router.get_external_transitions() == []
    _, _ = await router.run({"outcome": "name_given"})
    assert router.current_stage_name == "_end_"


@pytest.mark.asyncio
async def test_router_external_transition():
    router = IntentRouter(
        {
            "stages": {
                "ask_for_name": {
                    "accessible_from": ["_start_"],
                    "goal": "Ask the user for their name",
                    "outcomes": {
                        "name_given": {
                            "description": "The user has given their name",
                            "move_to": "_end_",
                        }
                    },
                },
                "questions": {
                    "accessible_from": ["_all_"],
                    "description": "The user asks you a question.",
                    "goal": "Answer their question",
                    "outcomes": {
                        "no_more_questions": {
                            "description": "The user has no more questions",
                            "move_to": "_backtrack_",
                        }
                    },
                },
            }
        }
    )
    assert router.get_external_transitions() == ["questions"]
    _, _ = await router.run({"outcome": "questions"})
    assert router.current_stage_name == "questions"


@pytest.mark.asyncio
async def test_router_simple_backtracking():
    router = IntentRouter(
        {
            "stages": {
                "ask_for_name": {
                    "accessible_from": ["_start_"],
                    "goal": "Ask the user for their name",
                    "outcomes": {
                        "name_given": {
                            "description": "The user has given their name",
                            "move_to": "_end_",
                        }
                    },
                },
                "questions": {
                    "accessible_from": ["_all_"],
                    "description": "The user asks you a question.",
                    "goal": "Answer their question",
                    "outcomes": {
                        "no_more_questions": {
                            "description": "The user has no more questions",
                            "move_to": "_backtrack_",
                        }
                    },
                },
            }
        }
    )
    assert router.get_external_transitions() == ["questions"]
    _, _ = await router.run({"outcome": "questions"})
    assert router.current_stage_name == "questions"

    assert router.get_external_transitions() == []
    _, _ = await router.run({"outcome": "no_more_questions"})
    assert router.current_stage_name == "ask_for_name"
