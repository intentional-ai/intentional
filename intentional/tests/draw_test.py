# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
from textwrap import dedent
import pytest
from intentional_core import IntentRouter
from intentional.draw import to_mermaid_diagram


@pytest.mark.parametrize(
    "router,diagram",
    [
        pytest.param(
            IntentRouter(
                {
                    "stages": {
                        "ask_for_name": {
                            "accessible_from": ["_start_"],
                            "goal": "Ask the user for their name",
                            "outcomes": {
                                "success": {
                                    "description": "The user says their name",
                                    "move_to": "_end_",
                                },
                                "failure": {
                                    "description": "The user states clearly they're not going to share their name",
                                    "move_to": "_end_",
                                },
                            },
                        }
                    }
                }
            ),
            dedent(
                """\
                ask_for_name["<b>ask_for_name</b>"] -- success --> _end_["<b>_end_</b>"]
                START("<b>start</b>"):::highlight ---> ask_for_name["<b>ask_for_name</b>"]
                ask_for_name["<b>ask_for_name</b>"] -- failure --> _end_["<b>_end_</b>"]"""
            ),
            id="single stage",
        ),
        pytest.param(
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
            ),
            dedent(
                """\
                ask_for_name["<b>ask_for_name</b>"] -- success --> ask_for_age["<b>ask_for_age</b>"]
                START("<b>start</b>"):::highlight ---> ask_for_name["<b>ask_for_name</b>"]
                ask_for_name["<b>ask_for_name</b>"] -- failure --> _end_["<b>_end_</b>"]
                ask_for_age["<b>ask_for_age</b>"] -- success --> _end_["<b>_end_</b>"]
                ask_for_age["<b>ask_for_age</b>"] -- failure --> _end_["<b>_end_</b>"]"""
            ),
            id="two connected stages",
        ),
        pytest.param(
            IntentRouter(
                {
                    "stages": {
                        "ask_for_name": {
                            "accessible_from": ["_start_"],
                            "goal": "Ask the user for their name",
                            "outcomes": {
                                "success": {
                                    "description": "The user says their name",
                                    "move_to": "_end_",
                                },
                                "failure": {
                                    "description": "The user states clearly they're not going to share their name",
                                    "move_to": "_end_",
                                },
                            },
                        },
                        "questions": {
                            "accessible_from": ["_all_"],
                            "description": "The user asked a question",
                            "goal": "Answer the user until they have no more questions",
                            "outcomes": {
                                "success": {
                                    "description": "The user has no more questions",
                                    "move_to": "_backtrack_",
                                },
                            },
                        },
                    }
                }
            ),
            dedent(
                """\
                ask_for_name["<b>ask_for_name</b>"] -- success --> _end_["<b>_end_</b>"]
                START("<b>start</b>"):::highlight ---> ask_for_name["<b>ask_for_name</b>"]
                ask_for_name["<b>ask_for_name</b>"] -- failure --> _end_["<b>_end_</b>"]
                questions["<b>questions</b>"] -- success --> BACKTRACK1("<b>backtrack</b>"):::highlight
                ALL2("<b>all</b>"):::highlight ---> questions["<b>questions</b>"]"""
            ),
            id="start stage + external stage",
        ),
    ],
)
def test_draw(router, diagram):
    raw_diagram = to_mermaid_diagram(router)
    raw_diagram = (
        raw_diagram.replace("graph TD;", "")
        .replace("classDef highlight fill:#aaf,stroke:#aaf;", "")
        .replace("\n\n", "\n")
        .strip()
    )
    assert raw_diagram == diagram
