#===============================================================================
#
#  Flatmap server tools
#
#  Copyright (c) 2019 - 2023  David Brooks
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

import argparse
from json import JSONDecodeError
from pprint import pprint

#===============================================================================

import requests

#===============================================================================

ENDPOINTS = {
    'production': 'https://mapcore-demo.org/current/flatmap/v3/',
    'staging': 'https://mapcore-demo.org/staging/flatmap/v1/',
    'fccb': 'https://mapcore-demo.org/fccb/flatmap/',
    'development': 'https://mapcore-demo.org/devel/flatmap/v4/',
}

#===============================================================================

LOOKUP_TIMEOUT = 30    # seconds; for `requests.get()`

#===============================================================================

def get_map_list(endpoint, **kwds):
    if not endpoint.startswith('http'):
        endpoint = ENDPOINTS[endpoint]
    try:
        response = requests.get(endpoint,
                                headers={'Accept': 'application/json'},
                                timeout=LOOKUP_TIMEOUT,
                                **kwds)
        if response.status_code == requests.codes.ok:
            try:
                return response.json()
            except JSONDecodeError:
                error = 'Invalid JSON returned'
        else:
            error = response.reason
    except requests.exceptions.RequestException as exception:
        error = f'Exception: {exception}'
    return [{'error': error}]


def latest_maps(endpoint):
    maps = get_map_list(endpoint)
    if len(maps) and (error := maps[0].get('error')) is not None:
        raise IOError(f'{endpoint}: {error}')
    latest_maps = {}
    for map in maps:
        key = (map.get('taxon', map['id']), map.get('biologicalSex'))
        if (key not in latest_maps
         or latest_maps[key]['created'] < map['created']):
            latest_maps[key] = map
    return latest_maps

#===============================================================================

def main():
    parser = argparse.ArgumentParser(description='List latest maps on a map server')
    parser.add_argument('--diff', metavar='SERVER', help=f'Flatmap server to compare with, values as for ENDPOINT')
    parser.add_argument('endpoint', metavar='ENDPOINT', help=f'Server endpoint, either one of {list(ENDPOINTS.keys())} or a `http:` url')
    args = parser.parse_args()
    if not args.endpoint.startswith('http') and args.endpoint not in ENDPOINTS:
        parser.error('Invalid ENDPOINT')
    elif args.diff is not None and not args.diff.startswith('http') and args.diff not in ENDPOINTS:
        parser.error('Invalid server endpoint to compare with')

    maps = latest_maps(args.endpoint)

    if args.diff is None:
        if args.endpoint.startswith('http'):
            text = f'at {args.endpoint}'
        else:
            text = f'on {args.endpoint} ({ENDPOINTS[args.endpoint]})'
        print(f'Latest maps {text}')
        pprint(maps)
    else:
        other_maps = latest_maps(args.diff)
        missing_other = []
        used_other = []
        print(f'UUID differences between latest maps on {args.endpoint} and {args.diff}:')
        print()
        for key, map in maps.items():
            if key in other_maps:
                used_other.append(key)
                if (map == other_maps[key]
                 or 'uuid' in map and map.get('uuid') == other_maps[key].get('uuid')):
                    pass
                else:
                    print(f'{args.endpoint}:')
                    pprint(map)
                    print(f'{args.diff}:')
                    pprint(other_maps[key])
                    print()
            else:
                missing_other.append(key)

        print(f'Latest maps missing from {args.diff}:')
        for key in missing_other:
            pprint(maps[key])
        print()
        print(f'Additional latest maps on {args.diff}:')
        for key, map in other_maps.items():
            if key not in used_other:
                pprint(map)

#===============================================================================

if __name__ == '__main__':
#=========================
    main()

#===============================================================================
