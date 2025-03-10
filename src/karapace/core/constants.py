"""
karapace - constants

Copyright (c) 2023 Aiven Ltd
See LICENSE for details
"""

from typing import Final

SCHEMA_TOPIC_NUM_PARTITIONS: Final = 1
TOPIC_CREATION_TIMEOUT_S: Final = 20
DEFAULT_SCHEMA_TOPIC: Final = "_schemas"
DEFAULT_PRODUCER_MAX_REQUEST: Final = 1048576
DEFAULT_AIOHTTP_CLIENT_MAX_SIZE: Final = 1048576

SECOND: Final = 1000
MINUTE: Final = 60 * SECOND
