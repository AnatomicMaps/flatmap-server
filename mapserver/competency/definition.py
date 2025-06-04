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

from collections import defaultdict
from pathlib import Path
import re
from typing import NotRequired, Optional, TypedDict
import yaml

#===============================================================================
#===============================================================================

class QueryParameter(TypedDict):
    column: str
    value: str | list[str]
    negate: NotRequired[bool]

#===============================================================================

class QueryError(TypedDict):
    error: str

class QueryRequest(TypedDict):
    query_id: str
    parameters: NotRequired[list[QueryParameter]]
    order: NotRequired[list[str]]
    limit: NotRequired[int]

class QueryResultRows(TypedDict):
    keys: list[str]
    values: list[list[str]]

class QueryResults(TypedDict):
    query_id: str
    results: QueryResultRows

#===============================================================================
#===============================================================================

class ParameterChoiceDict(TypedDict):
    label: str
    value: str

class ParameterDefinitionDict(TypedDict):
    column: str
    label: str
    type: NotRequired[str]
    choices: NotRequired[list[ParameterChoiceDict]]
    multiple: NotRequired[bool]
    default: NotRequired[str]

#===============================================================================

class ResultDefinitionDict(TypedDict):
    key: str
    label: NotRequired[str]
    type: NotRequired[str]

#===============================================================================

class QueryDefinitionSummary(TypedDict):
    id: str
    label: str
    description: NotRequired[str]

class QueryDefinitionDict(QueryDefinitionSummary):
    parameters: NotRequired[list[ParameterDefinitionDict]]
    results: list[ResultDefinitionDict]

#===============================================================================
#===============================================================================

CONDITION_MATCH = re.compile(r'%(CONDITION[A-Z,a-z,0-9,_]*)%')

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

    @property
    def sql(self):
        return self.__sql

#===============================================================================

class SqlParams:
    def __init__(self):
        self.__param_number = 1
        self.__params: list[str] = []

    @property
    def params(self):
        return self.__params

    def add_params(self, params: list[str]) -> str:
    #==============================================
        placeholders = ', '.join([f'${n}' for n in range(self.__param_number,
                                                         self.__param_number + len(params))])
        self.__param_number += len(params)
        self.__params.extend(params)
        return placeholders

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
        self.__id = defn['id']
        self.__column = defn['column']
        self.__condition = defn.get('condition', sql_conditions[-1])
        if self.__condition not in sql_conditions:
            raise ValueError(f'Query parameter has unknown condition: {self.__condition}')
        self.__label = defn['label']
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
        self.__multiple = defn.get('multiple')
        self.__default_msg = defn.get('default_msg')
        self.__default_sql = defn.get('default_sql')
        if (self.__default_msg is not None and self.__default_sql is None
         or self.__default_msg is not None and self.__default_sql is None):
            raise ValueError(f'Optional parameter `{self.__column}` must have both a default message and SQL')

    @property
    def as_dict(self) -> ParameterDefinitionDict:
    #============================================
        defn: ParameterDefinitionDict = {
            'column': self.__id,
            'label': self.__label
        }
        if self.__type is not None:
            defn['type'] = self.__type
        if self.__choices is not None:
            defn['choices'] = self.__choices
        if self.__multiple is not None:
            defn['multiple'] = self.__multiple
        if self.__default_msg is not None:
            defn['default'] = self.__default_msg
        return defn

    @property
    def column(self):
        return self.__column

    @property
    def condition(self):
        return self.__condition

    @property
    def optional(self):
        return self.__default_msg is not None

    @property
    def default_sql(self):
        return self.__default_sql.strip() if self.__default_sql is not None else ''

#===============================================================================

class QueryDefinition:
    def __init__(self, defn: dict):
        self.__id = defn['id']
        self.__label = defn['label']
        self.__description = defn.get('description')
        self.__sql_defn = SqlDefinition(defn['sql'])
        if self.__sql_defn.has_conditions:
            self.__parameters = { param_def['id']: ParameterDefinition(param_def, self.__sql_defn.conditions)
                                    for param_def in defn['parameters'] }
        else:
            self.__parameters = {}
        self.__results: dict[str, ResultDefinitionDict] = { rdef['key']: rdef for rdef in defn['results'] }

    @property
    def as_dict(self) -> QueryDefinitionDict:
    #========================================
        defn: QueryDefinitionDict = {
            'id': self.__id,
            'label': self.__label,
            'results': list(self.__results.values())
        }
        if self.__description is not None:
            defn['description'] = self.__description
        if len(self.__parameters):
            defn['parameters'] = [param_def.as_dict for param_def in self.__parameters.values()]
        return defn

    @property
    def result_keys(self) -> list[str]:
    #==================================
        return list(self.__results.keys())

    @property
    def summary(self) -> QueryDefinitionSummary:
    #===========================================
        summary: QueryDefinitionSummary = {
            'id': self.__id,
            'label': self.__label
        }
        if self.__description is not None:
            summary['description'] = self.__description
        return summary

    def make_sql(self, request: QueryRequest) -> tuple[str, list[str]]:
    #==================================================================
        conditions = defaultdict(list)
        sql_params = SqlParams()
        used_columns = []
        if (req_params := request.get('parameters')) is not None:
            for req_param in req_params:
                column_id = req_param['column']
                if (param_def := self.__parameters.get(column_id)) is None:
                    raise ValueError(f'Unknown parameter in request: {column_id}')
                column = param_def.column
                req_values = req_param.get('value')
                if isinstance(req_values, list):
                    if len(req_values) == 0:
                        req_values = None
                    elif len(req_values) == 1:
                        req_values = req_values[0]
                if isinstance(req_values, list):
                    negate = ' NOT' if req_param.get('negate', False) else ''
                    where_condition = f'{column}{negate} IN ({sql_params.add_params(req_values)})'
                elif req_values is not None:
                    negate = '!' if req_param.get('negate', False) else ''
                    where_condition = f'{column} {negate}= {sql_params.add_params([req_values])}'
                elif not param_def.optional:
                    raise ValueError(f'Required parameter must have a value: {column}')
                else:
                    negate = '!' if req_param.get('negate', False) else ''
                    where_condition = f'{column} {negate}= ({param_def.default_sql})'
                conditions[param_def.condition].append(where_condition)
                used_columns.append(column_id)
        # NB. req_params might/will not have entries for default params
        for column_id, param_def in self.__parameters.items():
            if column_id not in used_columns:
                if not param_def.optional:
                    raise ValueError(f'Required parameter must have a value: {column_id}')
                where_condition = f'{param_def.column} = ({param_def.default_sql})'
                conditions[param_def.condition].append(where_condition)
        sql = self.__sql_defn.sql
        for condition, expressions in conditions.items():
            sql = sql.replace(f'%{condition}%', ' AND '.join(expressions))
        if (ordering := request.get('order')) is not None and len(ordering):
            sql += f" ORDER BY {', '.join(ordering)}"
        if (limit := int(request.get('limit', 0))):
            sql += f' LIMIT {limit}'
        return (sql, sql_params.params)

#===============================================================================

def load_query_definitions(queries_directory: str) -> dict[str, QueryDefinition]:
#================================================================================
    result = {}
    for query_file in Path(queries_directory).glob('*.yaml'):
        with open(query_file) as fp:
            try:
                definitions = yaml.safe_load(fp)
                if 'queries' not in definitions:
                    raise ValueError(f'No queries block in {query_file}...')
                for defn in definitions['queries']:
                    if 'id' in defn:
                        result[str(defn['id'])] = QueryDefinition(defn)
                    else:
                        raise ValueError(f'Query definitions must have `id`s')
            except yaml.YAMLError as err:
                raise ValueError(f'Error parsing query definitions: {err}')
    return result

#===============================================================================
