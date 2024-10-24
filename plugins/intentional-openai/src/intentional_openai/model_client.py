# SPDX-FileCopyrightText: 2024-present ZanSara <github@zansara.dev>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Model client for OpenAI models.
"""

from typing import Optional
import os
import logging

import openai
from intentional_core import ModelClient
from intentional_openai.realtime_api import RealtimeAPIClient


logger = logging.getLogger(__name__)


class OpenAIClient(ModelClient):
    """
    Model client for OpenAI models.
    """

    name: Optional[str] = "openai"

    def __init__(self, config):
        logger.debug("Loading OpenAIClient from config: %s", config)

        self.model_name = config.get("name")
        if not self.model_name:
            raise ValueError("OpenAIClient requires a 'name' configuration key to know which model to use.")

        self.api_key_name = config.get("api_key_name", "OPENAI_API_KEY")
        if not os.environ.get(self.api_key_name):
            raise ValueError(
                "OpenAIClient requires an API key to authenticate with OpenAI. "
                f"The provided environment variable name ({self.api_key_name}) is not set or is empty."
            )

        self.model_init_params = config.get("init_params", {})

        if "realtime" in self.model_name:
            self.client = RealtimeAPIClient()
        else:
            self.client = openai.AsyncOpenAI(**self.model_init_params, api_key=os.environ[self.api_key_name])

    def __getattr__(self, name):
        return getattr(self.client, name)
