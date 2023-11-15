#===============================================================================
#
#  Flatmap viewer and annotation tools
#
#  Copyright (c) 2019-2023  David Brooks
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#===============================================================================

from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
import json
import os
import sqlite3

import flask            # type: ignore

from .pennsieve import user_data
from .server import annotator_blueprint, settings

#===============================================================================

AUTHENTICATED_COOKIE  = 'annotation-authenticated'
UPDATE_ALLOWED_COOKIE = 'update-allowed'
COOKIE_MAX_AGE        = 86400   # seconds, one day

#===============================================================================

