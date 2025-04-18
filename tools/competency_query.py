#===============================================================================
#
#  Flatmap server
#
#  Copyright (c) 2019-25  David Brooks
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
import json
from typing import NotRequired, Optional, TypedDict

from pprint import pprint

#===============================================================================

from prompt_toolkit import PromptSession
from prompt_toolkit import print_formatted_text, HTML
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style
import requests

#===============================================================================

__version__ = '0.1.0'

#===============================================================================

COMMAND_INPUT_STYLE = '#ff0066'

#===============================================================================

REQUEST_TIMEOUT = 10

#===============================================================================

QUERY_ENDPOINT = '/competency/query'

QUERY_DEFINITIONS_ENDPOINT = '/competency/queries'

#===============================================================================

class QueryParameter(TypedDict):
    column: str
    value: str | list[str]
    negate: NotRequired[bool]

#===============================================================================

class QueryRequest(TypedDict):
    query_id: str
    parameters: NotRequired[list[QueryParameter]]
    order: NotRequired[list[str]]
    limit: NotRequired[int]

#===============================================================================

class CompetencyQueryService:
    def __init__(self, map_server: str):
        self.__map_server = map_server

    def request_json(self, method: str, endpoint: str, **kwds) -> dict|list:
    #=======================================================================
        endpoint = self.__map_server + endpoint
        try:
            response = requests.request(method, endpoint,
                                    headers={'Accept': 'application/json'},
                                    timeout=REQUEST_TIMEOUT,
                                    **kwds)
            if response.status_code == requests.codes.ok:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    error = 'Invalid JSON returned for request'
            else:
                error = f'Request error: {response.reason}'
        except requests.exceptions.RequestException as exception:
            error = f'Exception: {exception}'
        print(error)
        return []

    def get_json(self, endpoint: str, param: Optional[str]=None) -> dict|list:
    #=========================================================================
        if param is not None:
            endpoint += f'/{param}'
        return self.request_json('GET', endpoint)

    def post_query(self, request: QueryRequest) -> dict|list:
    #========================================================
        # also need to set content-type header??
        return self.request_json('POST', QUERY_ENDPOINT, data=request)

#===============================================================================

class CompetencyQueryShell:
    intro = 'Welcome to the Competency Query shell. Type help or ? to list commands.\n'

    def __init__(self, map_server: str):
        self.__query_service = CompetencyQueryService(map_server)
        self.__queries = { str(query['id']): query['label']
                            for query in self.__query_service.get_json(QUERY_DEFINITIONS_ENDPOINT)
                                if 'id' in query }
        self.__cmd_session = PromptSession(message=FormattedText([('class:prompt', 'cq> ')]),
                                           style=Style.from_dict({'prompt': '#eeeeee bold',
                                                                  '': COMMAND_INPUT_STYLE}))
        self.__input_session = PromptSession(style=Style.from_dict({'prompt': '#eeeeee bold'}))

    def __do_query(self, id_text: list[str]):
    #========================================
        if len(id_text) == 0:
            query_id = self.__get_input('ID? ')
            if query_id is None or query_id == '':
                return
        else:
            query_id = id_text[0]
        if query_id not in self.__queries:
            print('Unknown query ID...')
        else:
            query = self.__query_service.get_json(QUERY_DEFINITIONS_ENDPOINT, query_id)
            if len(query) == 0:
                print('Error when getting query definition...')
            else:
                pprint(query)

    def __list_queries(self):
    #========================
        print_formatted_text(HTML('<b>ID\tName</b>'))
        for (id, label) in self.__queries.items():
            print(f'{id}\t{label}')

    def __get_command(self) -> Optional[str]:
    #========================================
        try:
            return self.__cmd_session.prompt().strip()
        except KeyboardInterrupt:
            return ''
        except EOFError:
            return None

    def __get_input(self, prompt: str) -> Optional[str]:
    #===================================================
        try:
            return self.__input_session.prompt(FormattedText([("class:prompt", prompt)])).strip()
        except KeyboardInterrupt:
            return ''
        except EOFError:
            return None

    def help(self):
    #=============
        print('queries       Show available queries.')  ## coloured...
        print('query ID      Run query with ID.')  ## coloured...

    def run(self):
    #=============
        print(self.intro)
        while True:
            cmd = self.__get_command()
            if cmd is None:
                break
            elif cmd == '':
                continue
            elif cmd == '?' or cmd == 'help':
                self.help()
            elif cmd == 'queries':
                self.__list_queries()
            elif cmd == 'query' or cmd.startswith('query '):
                self.__do_query(cmd.split()[1:])
            else:
                print(f'Unknown command... `{cmd}`')
        print('GoodBye!')

#===============================================================================

def main():
    parser = argparse.ArgumentParser(description='xxxx')
    # version
    parser.add_argument('server', metavar='MAP_SERVER', help='Map server URL')
    args = parser.parse_args()

    CompetencyQueryShell(args.server).run()

#===============================================================================

if __name__ == '__main__':
#=========================
    main()

#===============================================================================
