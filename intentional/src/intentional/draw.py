# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Helpers that allow the user to draw the bot's graph.
"""

import base64
from pathlib import Path

import requests
import structlog
from intentional_core.intent_routing import IntentRouter


log = structlog.get_logger(logger_name=__name__)


MERMAID_STYLED_TEMPLATE = """
graph TD;

{connections}

classDef special fill:#aaf,stroke:#aaf;
"""


async def to_image(intent_router: IntentRouter, image_path: Path) -> None:
    """
    Saves an image of the intent's graph at the given path.

    Args:
        intent_router: the intents graph to draw.
        image_path: where to save the resulting image
    """
    image = await to_bytes(intent_router)
    with open(image_path, "wb") as imagefile:
        imagefile.write(image)


async def to_bytes(intent_router: IntentRouter, mermaid_domain: str = "https://mermaid.ink/img/") -> bytes:
    """
    Uses mermaid.ink to render the intent's graph into an image.

    Args:
        intent_router: the intents graph to draw.
        mermaid_domain: the domain of your Mermaid instance, if you have your own.
            Defaults to the public mermaid.ink domain.

    Returns:
        The bytes of the resulting image. To save them into an image file, do:

        ```python
        image = to_image(intent_router)
        with open(image_path, "wb") as imagefile:
            imagefile.write(image)
        ```
    """
    url = to_mermaid_link(intent_router, mermaid_domain)
    resp = requests.get(url, timeout=10)
    if resp.status_code >= 400:
        resp.raise_for_status()
    return resp.content


def to_mermaid_link(intent_router: IntentRouter, mermaid_domain: str = "https://mermaid.ink/img/") -> str:
    """
    Generated a URL that contains a rendering of the graph of the intents into an image.

    Args:
        intent_router: the intents graph to draw.
        mermaid_domain: the domain of your Mermaid instance, if you have your own.
            Defaults to the public mermaid.ink domain.

    Returns:
        A URL on Mermaid.ink with the graph of the intents.
    """
    graph_styled = to_mermaid_diagram(intent_router)
    graphbytes = graph_styled.encode("ascii")
    base64_bytes = base64.b64encode(graphbytes)
    base64_string = base64_bytes.decode("ascii")
    return mermaid_domain + base64_string


def to_mermaid_diagram(intent_router: IntentRouter) -> str:
    """
    Creates a textual representation of the intents graph in a way that Mermaid.ink can render.

    Keep in mind that this function should be able to render also malformed graphs as
    far as possible, because it can be used as a debugging tool to visualize bad bot
    configurations within error messages.

    Args:
        intent_router: the intents graph to draw.

    Returns:
        A string containing the description of the graph.
    """
    stages = {node: f'{node}["<b>{node}</b>"]' for node in intent_router.stages}
    unique_counter = 0
    connections_list = []

    processed_nodes = set()
    for origin, target, key in intent_router.graph.edges:
        # 'end' is reserved in Mermaid
        if target == "end":
            edge_string = f'{stages[origin]} -- {key} --> END["<b>end</b>"]'
        elif target == "_backtrack_":
            unique_counter += 1
            edge_string = f'{stages[origin]} -- {key} --> BACKTRACK{unique_counter}("<b>backtrack</b>"):::special'

        else:
            edge_string = f"{stages[origin]} -- {key} --> {stages.get(target, target)}"
        connections_list.append(edge_string)

        # Indirect connections
        if origin not in processed_nodes:
            processed_nodes.add(origin)

            if intent_router.stages[origin].accessible_from == ["_start_"]:
                edge_string = f'START("<b>start</b>"):::special ---> {stages[origin]}'
            elif intent_router.stages[origin].accessible_from == ["_all_"]:
                unique_counter += 1
                edge_string = f'ALL{unique_counter}("<b>all</b>"):::special ---> {stages[origin]}'
            elif intent_router.stages[origin].accessible_from:
                unique_counter += 1
                accessible_from_str = ",<br>".join(intent_router.stages[origin].accessible_from)
                edge_string = f'FROM{unique_counter}("<b>{accessible_from_str}</b>"):::special ---> {stages[origin]}'
            else:
                continue
            connections_list.append(edge_string)

    connections = "\n".join(connections_list)
    graph_styled = MERMAID_STYLED_TEMPLATE.format(connections=connections)
    log.debug("Mermaid graph created", mermaid_graph=graph_styled)
    return graph_styled
