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
from typing import Iterable, NotRequired, Optional, TypedDict

from pprint import pprint

#===============================================================================

from prompt_toolkit import prompt as get_input, PromptSession
from prompt_toolkit import print_formatted_text, HTML
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style
import requests

#===============================================================================

__version__ = '0.1.0'

#===============================================================================

COMMAND_INPUT_STYLE = '#ff0066'

def print_bold_prefix(prefix: str, text: str=''):
#================================================
    print_formatted_text(HTML(f'<b>{prefix}</b>{text}'))

def print_table(header: list[str], rows: Iterable[Iterable[str]]):
#=================================================================
    print_bold_prefix('\t'.join(header))
    for row in rows:
        print('\t'.join(row))

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
            if response.ok:
                try:
                    query_response = response.json()
                    if 'error' in query_response:
                        error = query_response['error']
                    else:
                        return query_response
                except json.JSONDecodeError:
                    error = 'Invalid JSON returned for request'
            else:
                error = f'HTTP error for request: {response.status_code} {response.reason}'
        except requests.exceptions.RequestException as exception:
            error = f'Exception: {exception}'
        print_formatted_text(FormattedText([('class:error', error),]),
                                           style=Style.from_dict({'error': '#ff0000 bold'}))
        return []

    def get_json(self, endpoint: str, param: Optional[str]=None) -> dict|list:
    #=========================================================================
        if param is not None:
            endpoint += f'/{param}'
        return self.request_json('GET', endpoint)

    def post_query(self, request: QueryRequest) -> dict|list:
    #========================================================
        return self.request_json('POST', QUERY_ENDPOINT, json=request)

#===============================================================================

class CompetencyQueryShell:
    intro = 'Welcome to the Competency Query shell. Type help or ? to list commands.\n'

    def __init__(self, map_server: str):
        self.__query_service = CompetencyQueryService(map_server)
        self.__queries: dict[str, str] = { str(query['id']): str(query['label'])
                                            for query in self.__query_service.get_json(QUERY_DEFINITIONS_ENDPOINT)
                                                if 'id' in query }
        self.__cmd_session = PromptSession(message=HTML('<p fg="ansiwhite"><b>cq> </b></p>'),
                                           style=Style.from_dict({'': COMMAND_INPUT_STYLE}))
        self.__input_session = PromptSession()

    def __list_queries(self):
    #========================
        print_table(['ID', 'Name'], list(self.__queries.items()))

    def __query_command(self, id_text: list[str]):
    #=============================================
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
            if len(query) == 0 or isinstance(query, list):
                print('Error when getting query definition...')
            else:
                self.__run_query(query)

    def __get_query_parameters(self, parameter_definitions: list) -> Optional[list[QueryParameter]]:
    #===============================================================================================
        query_parameters: list[QueryParameter] = []
        for parameter in parameter_definitions:
            column = parameter['column']
            default_msg = parameter.get('default')
            query_parameter: Optional[QueryParameter] = None
            if parameter.get('multiple', False):
                values: list[str] = []
                print_bold_prefix('IN> ', f"Please enter one or more {parameter['label']} or ? for help:")
                if default_msg is not None:
                    print('    ', f'If none are given {default_msg}')
                while True:
                    input = self.__get_input('')
                    if input is None or input == '':
                        break
                    elif input[0] == '?':
                        print('Input can be space or comma separated, or over multiple lines.')
                        print('An empty line terminates input.')
                    else:
                        values.extend(input.replace(',', ' ').split())
                if len(values) == 0:
                    if default_msg is None:
                        print('No values entered for a required parameter -- aborting query')
                        return None
                else:
                    query_parameter = {'column': column, 'value': values}
            else:
                message = [f"Please enter {parameter['label']}"]
                if default_msg is not None:
                    message.append(f' -- if none is given {default_msg}')
                message.append(':')
                print_bold_prefix('IN> ', ''.join(message))
                input = self.__get_input('')
                if input is None or input == '':
                    if default_msg is None:
                        print('No value entered for a required parameter -- aborting query')
                        return None
                else:
                    query_parameter = {'column': column, 'value': input}
            if query_parameter is not None:
                input = self.__get_input('Optionally negate the input condition: N/y? ', False)
                if input  in ['Y', 'y']:
                    query_parameter['negate'] = True
                query_parameters.append(query_parameter)
        return query_parameters

    def __get_query_order(self, result_columns: list[str]) -> list[str]:
    #===================================================================
        ordering: list[str] = []
        input = self.__get_input('Optionally specify the order of result rows: N/y? ', False)
        if input in ['Y', 'y']:
            while True:
                print_bold_prefix('IN> ', f'Please enter one or more result columns or ? for help:')
                while True:
                    input = self.__get_input('')
                    if input is None or input == '':
                        break
                    elif input[0] == '?':
                        print(f'Result columns are: {result_columns}')
                        print('Input can be space or comma separated, or over multiple lines.')
                        print('An empty line terminates input.')
                    else:
                        for column in input.replace(',', ' ').split():
                            if column not in result_columns:
                                print(f'{column} is not a result column')
                            else:
                                ordering.append(column)
        return ordering

    def __get_query_limit(self) -> Optional[int]:
    #============================================
        input = self.__get_input('Optionally limit the number of result rows: N/y? ', False)
        if input in ['Y', 'y']:
            input = self.__get_input(f'Please enter a number (0 or an invalid number means no limit): ', False)
            if input is not None:
                try:
                    return int(input.split()[0])
                except ValueError:
                    pass
        return None

    def __run_query(self, query: dict):
    #==================================
        print_bold_prefix(f"Query \"{query['label']}\"")
        query_request: QueryRequest = {'query_id': str(query['id'])}
        query_parameters = self.__get_query_parameters(query['parameters'])
        if query_parameters is None:
            return
        if len(query_parameters):
            query_request['parameters'] = query_parameters
        result_definitions = { definition['key']: definition
                                for definition in query['results'] }
        ordering = self.__get_query_order(list(result_definitions.keys()))
        if len(ordering):
            query_request['order'] = ordering
        limit = self.__get_query_limit()
        if limit is not None and limit > 0:
            query_request['limit'] = limit
        result_set = self.__query_service.post_query(query_request)
        if isinstance(result_set, dict):
            results = result_set['results']
            print_table([result_definitions[key]['label'] for key in results['keys']],
                        results['values'])

    def __get_command(self) -> Optional[str]:
    #========================================
        try:
            return self.__cmd_session.prompt().strip()
        except KeyboardInterrupt:
            return ''
        except EOFError:
            return None

    def __get_input(self, prompt: str, bold=True) -> Optional[str]:
    #==============================================================
        try:
            if bold:
                return self.__input_session.prompt(HTML(f'<b>{prompt}</b>')).strip()
            else:
                return get_input(prompt).strip()
        except KeyboardInterrupt:
            return ''
        except EOFError:
            return None

    def help(self):
    #=============
        print('queries       Show available queries.')
        print('query ID      Run query with given ID.')

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
                self.__query_command(cmd.split()[1:])
            else:
                print('Unknown command...')
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
