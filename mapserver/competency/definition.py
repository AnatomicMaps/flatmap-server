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

import re
from typing import NotRequired, Optional, TypedDict
import yaml

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

CONDITION_MATCH = re.compile(r'%(CONDITION_[A-Z,a-z,0-9,_]*)%')
class ParameterChoiceDict(TypedDict):
    label: str
    value: str

class SqlDefinition:
    def __init__(self, sql: str):
        self.__sql = sql
        self.__conditions = CONDITION_MATCH.findall(sql)

    @property
    def conditions(self):
        return self.__conditions

    @property
    def has_conditions(self):
        return len(self.__conditions) > 0

#===============================================================================


#===============================================================================

PARAMETER_TYPES = [
    'string',
    'number',
    'boolean',
    'choice',
    'multichoice'
]

class ParameterDefinition:
    def __init__(self, defn: dict, sql_conditions: list[str]):
        self.__column = defn['column']
        self.__condition = defn.get('condition', sql_conditions[-1])
        if self.__condition not in sql_conditions:
            raise ValueError(f'Query parameter has unknown condition: {self.__condition}')
        self.__label = defn['label']
        self.__description = defn.get('description')
        self.__type = defn.get('type', 'string')
        if not self.__type in PARAMETER_TYPES:
            raise ValueError(f'Invalid type of query parameter: {self.__type}')
        if 'choice' in self.__type:
            self.__choices: Optional[list[ParameterChoiceDict]] = [{
                'label': choice['label'],
                'value': choice['value']
            } for choice in defn['choices']]
        else:
            self.__choices = None
        self.__optional = defn.get('optional', False)

#===============================================================================

class QueryDefinition:
    def __init__(self, defn: dict):
        self.__id = defn['id']
        self.__label = defn['label']
        self.__description = defn.get('description')
        self.__sql = SqlDefinition(defn['sql'])
        if self.__sql.has_conditions:
            self.__parameters = { param_def['column']: ParameterDefinition(param_def, self.__sql.conditions)
                                    for param_def in defn['parameters'] }
        else:
            self.__parameters = {}

    def make_sql(self, request: QueryRequest) -> tuple[str, list[str]]:
    #==================================================================

        conditions = []

        for param_def in self.__parameters:
            pass

        if request.parameters is not None:
            for parameter in request.parameters:
                if (param_def := self.__parameters.get(parameter.column)) is not None:
                    pass

        # append ' AND '.join(conditions)

        # add any ``order``

        # add any ``limit``

        return ('', [])

#===============================================================================

def load_query_definitions(yaml_file: str) -> dict[str, QueryDefinition]:
#========================================================================
    result = {}
    with open(yaml_file) as fp:
        try:
            definitions = yaml.safe_load(fp)
            if 'queries' not in definitions:
                raise ValueError(f'No queries block in {yaml_file}...')
            for defn in definitions['queries']:
                if 'id' in defn:
                    result[defn['id']] = QueryDefinition(defn)
                else:
                    raise ValueError(f'Query definitions must have `id`s')
        except yaml.YAMLError as err:
            raise ValueError(f'Error parsing query definitions: {err}')
    return result

#===============================================================================
