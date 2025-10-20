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

import requests

#===============================================================================

from .settings import settings

#===============================================================================

# Default Pennsieve API endpoint

PENNSIEVE_API_PRODUCTION = 'https://api.pennsieve.io'

#===============================================================================

## Environment...
# export LOGIN_API_URL="https://api.pennsieve.io"
# export SPARC_ORGANISATION_ID=N:organization:618e8dd9-f8d2-4dc4-9abb-c6aaab2e78a0
# export SPARC_ORGANISATION_INT_ID=367
# export SPARC_ANNOTATION_TEAM_ID=N:team:031b434c-41ab-4ecf-92a9-050fc1b3211a

PENNSIEVE_API_ENDPOINT = os.environ.get('PENNSIEVE_API_ENDPOINT', PENNSIEVE_API_PRODUCTION)

SPARC_ORGANISATION_ID = os.environ.get('SPARC_ORGANISATION_ID')
SPARC_ORGANISATION_INT_ID = os.environ.get('SPARC_ORGANISATION_INT_ID')
SPARC_ANNOTATION_TEAM_ID = os.environ.get('SPARC_ANNOTATION_TEAM_ID')

__logged_missing_ids = False

#===============================================================================

def query(url, method: str='GET') -> Any:
    headers = {"accept": "*/*"}
    response = requests.request(method, url, headers=headers)
    if response.status_code == 200:
        try:
            return json.loads(response.text)
        except requests.exceptions.JSONDecodeError:
            pass
    return {
        'error': f'{response.status_code}: {response.reason}'
    }

#===============================================================================

def get_annotation_team(key: str) -> Optional[list[str]]:
    if SPARC_ORGANISATION_ID is None or SPARC_ORGANISATION_INT_ID is None or SPARC_ANNOTATION_TEAM_ID is None:
        global __logged_missing_ids
        if not __logged_missing_ids:
            settings['LOGGER'].warning('Pennsieve IDs of SPARC and MAP Annotation Team are not defined')
            __logged_missing_ids = True
        return None
    try:
        organization = query(f'{PENNSIEVE_API_ENDPOINT}/session/switch-organization?organization_id={SPARC_ORGANISATION_INT_ID}&api_key={key}', 'PUT')
    except Exception as e:
        settings['LOGGER'].warning(f"Failed to switch organization: {e}")
    team_query = query(f'{PENNSIEVE_API_ENDPOINT}/organizations/{SPARC_ORGANISATION_ID}/teams/{SPARC_ANNOTATION_TEAM_ID}/members?api_key={key}')
    if 'error' not in team_query:
        return [id for member in team_query if (id := member.get('id')) is not None]

#===============================================================================

def get_user(key: str) -> dict:
    annotation_team = get_annotation_team(key)
    user_query = query(f'{PENNSIEVE_API_ENDPOINT}/user/?api_key={key}')
    if 'error' in user_query:
        return user_query
    return {
        'name': ' '.join([user_query.get('firstName', ''), user_query.get('lastName', '')]),
        'email': user_query.get('email', ''),
        'orcid': user_query.get('orcid', {}).get('orcid', ''),
        'canUpdate': annotation_team is not None and user_query.get('id', '') in annotation_team
    }

#===============================================================================
