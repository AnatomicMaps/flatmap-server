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
from pprint import pprint

import requests

#===============================================================================

SPARC_ORGANISATION = 'N:organization:618e8dd9-f8d2-4dc4-9abb-c6aaab2e78a0'
KEAST_TEAM = 'N:team:e32b2168-a0c5-4564-8ed8-8ba1078421fd'

# Set by environment variables
ORGANISATION_ID = SPARC_ORGANISATION
TEAM_ID = KEAST_TEAM

# Comes from token in HTTP request
API_KEY = 'eyJraWQiOiJwcjhTaWE2dm9FZTcxNyttOWRiYXRlc3lJZkx6K3lIdDE4RGR5aGVodHZNPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiI5ZWQyMTY4MS1lNzQ5LTQ5NDUtOWVkOS1hOWM4NjA1YTBiNDYiLCJ0b2tlbl91c2UiOiJhY2Nlc3MiLCJzY29wZSI6Im9wZW5pZCIsImF1dGhfdGltZSI6MTY5NjkxMDQ3MSwiaXNzIjoiaHR0cHM6XC9cL2NvZ25pdG8taWRwLnVzLWVhc3QtMS5hbWF6b25hd3MuY29tXC91cy1lYXN0LTFfYjFOeXhZY3IwIiwiZXhwIjoxNjk2OTE0MDcxLCJpYXQiOjE2OTY5MTA0NzEsInZlcnNpb24iOjIsImp0aSI6ImE0YzU0MmNiLWEwYTUtNDg0Zi04NTAyLThjY2ExYTdjNGU3MCIsImNsaWVudF9pZCI6IjY3MG1vN3NpODFwY2Mzc2Z1YjdvMTkxNGQ4IiwidXNlcm5hbWUiOiI5ZWQyMTY4MS1lNzQ5LTQ5NDUtOWVkOS1hOWM4NjA1YTBiNDYifQ.LWmbP4iDT39Cdk8FCLLPtHT5KHfJ5FymDranCOONvJUIrdJsbm9j8iBc7NgPW5Hcmaw_-NdaZXLQe1ugD3e7VsROWzpbkyIZymizYVB-F5By6B_dmAt9yMh7QaFsUTyUzGyy3eD0M1fO7hQaPietKDY_Y09v2jBsmLR5n-NJaecMqU5-w6ZtGtjCJxEgWURJxlfj2qgvmDdDJ1s5qNUukFuHMFHYAGvpijhvX7A1g93EWtIV7BofIcj0GJtIdodHZEuzMRvsrgc_IDi35beBEzwnThW509Rl5hE1VmR7aPwr9R2uFgGiavWUUUTkGh9ukL4sujTiuSnx3lHmqaL_Fg'

#===============================================================================

def query(url):
    headers = {"accept": "*/*"}
    response = requests.get(url, headers=headers)
    return json.loads(response.text)

#===============================================================================

'''
# Or find Annotation team with:
TEAM_ID = NONE
teams = query(f'https://api.pennsieve.io/organizations/{ORGANISATION_ID}/teams?api_key={API_KEY}')
for team on teams['team']:
    if team['name'] == 'Annotation team':
        TEAM_ID = team['id']
        break
if TEAM_ID is None:
    pass
    # error....
'''

#===============================================================================

# Cache API_KEY to user/team membership, with time out of old API_KEYs (24 hours)?
# Cache team member table with say one hour timeout? Or (better?) update team members
# whenever API_KEY changes? (Then logout and back in when someone added to team in Pennsieve will
# see updated team.)

team_members = query(f'https://api.pennsieve.io/organizations/{ORGANISATION_ID}/teams/{TEAM_ID}/members?api_key={API_KEY}')
team_member_ids = [member['id'] for member in team_members]
print(team_member_ids)

user = query(f'https://api.pennsieve.io/user/?api_key={API_KEY}')
user_id = user.get('id', '')
if user_id in team_member_ids:
    user['annotator'] = True
    pprint(user)


#===============================================================================
