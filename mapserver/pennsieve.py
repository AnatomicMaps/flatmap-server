#===============================================================================
#
#  Flatmap server
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

import json
import os
from typing import Any, Optional

#===============================================================================

import flask
import requests

#===============================================================================

from .settings import settings

#===============================================================================

PENSIEVE_API = 'https://api.pennsieve.io'

#===============================================================================

## Environment...
# export SPARC_ORGANISATION_ID=N:organization:618e8dd9-f8d2-4dc4-9abb-c6aaab2e78a0
# export SPARC_ANNOTATION_TEAM_ID=N:team:031b434c-41ab-4ecf-92a9-050fc1b3211a

SPARC_ORGANISATION_ID = os.environ.get('SPARC_ORGANISATION_ID')
SPARC_ANNOTATION_TEAM_ID = os.environ.get('SPARC_ANNOTATION_TEAM_ID')

#===============================================================================

def query(url) -> Any:
    headers = {"accept": "*/*"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        try:
            return json.loads(response.text)
        except requests.exceptions.JSONDecodeError:
            pass
    return {
        'error': f'{response.status_code}: {response.reason}'
    }

#===============================================================================

annotation_team = None

def get_annotation_team(key: str) -> Optional[list[str]]:
    if SPARC_ORGANISATION_ID is None or SPARC_ANNOTATION_TEAM_ID is None:
        settings['LOGGER'].warning('Pennsieve IDs of SPARC and MAP Annotation Team are not defined')
    team_query = query(f'{PENSIEVE_API}/organizations/{SPARC_ORGANISATION_ID}/teams/{SPARC_ANNOTATION_TEAM_ID}/members?api_key={key}')
    if 'error' not in team_query:
        return [id for member in team_query if (id := member.get('id')) is not None]

#===============================================================================

def get_user(key: str) -> dict:
    global annotation_team
    if annotation_team is None:
        annotation_team = get_annotation_team(key)
    user_query = query(f'https://api.pennsieve.io/user/?api_key={key}')
    if 'error' in user_query:
        return user_query
    return {
        'name': ' '.join([user_query.get('firstName', ''), user_query.get('lastName', '')]),
        'email': user_query.get('email', ''),
        'orcid': user_query.get('orcid', {}).get('orcid', ''),
        'canUpdate': annotation_team is not None and user_query.get('id', '') in annotation_team
    }

#===============================================================================
