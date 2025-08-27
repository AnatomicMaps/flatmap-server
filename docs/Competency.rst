Competency Queries
==================

Query descriptions
------------------

A server's configuration has a set of YAML files that define the available queries, including
information to assist a frontend UI in obtaining user input and presenting result sets back
to a user.

::

    queries:
      - id: QUERY_ID            # Required
        label: A short label    # Required
        description: An optional description as to what this query is all about...
        #
        sql: SQL query with %CONDITION_ID% blocks for parameters    # Required
        #
        parameters:             # Required if `sql` has %CONDITION% blocks
          - column: COLUMN_ID           # Required
            condition: CONDITION_ID     # Optional, defaults to the last %CONDITION% block's id
            label: Human readable label # Required
            description: An optional longer description
            type: string                # Optional, defaults to `string`,
                                        # values `string``, `number`, `boolean`,
                                        # `choice` or `multichoice`
            choices:                    # Required when type is `choice` or `multichoice`
              - label: Human readable label     # Required
                value: Value when selected      # Required
            multiple: false             # Optional, defaults to `false`
            default_msg: string         # Optional; if specified the parameter is optional
            default_sql: string         # SQL query to get the default value if the parameter is optional
        #
        results:                # Required
          - key: RESULT_IDs             # Required
            label: Human readable label # Optional
            type: string                # Optional, defaults to `string`
        #


Server endpoints
----------------

.. openapi:: spec/openapi.yaml
   :include:
      /competency/queries

*   ``GET competency/queries`` returns a JSON list of available queries giving their ``id``, ``label`` and ``description``.
*   ``GET competency/queries/QUERY_ID`` returns details of a specific query from the query description, in JSON.

.. openapi:: spec/openapi.yaml
   :include:
      /competency/query

*   ``POST competency/query/`` expects JSON data in the form::

        {
            "query_id": "QUERY_ID",
            "parameters": [
                {
                    "column": "PARAM_1",
                    "value": ["multiple", "terms"]
                },
                {
                    "column": "PARAM_1",
                    "value": "single value",
                    "negate": true
                },
                {
                    .
                    .
                }
            ],
            "order": null         # Optional list of RESULT_IDs
            "limit": N            # Optional
            "comment": "Above becomes `(PARAM_1 in ('multiple', 'terms') AND PARAM_1 != 'single value')"
        }


    and returns::

        {
            "query_id": "QUERY_ID",
            "results": {
                "keys": ["RESULT_ID", ...],
                "values": [
                    ["RESULT_ID value from first result row", ...],
                    ["RESULT_ID value from second result row", ...],
                        .
                        .
                        .
                ]
            }
        }
