Competency Queries via a Flatmap Server
=======================================

Query descriptions
------------------

A server's configuration will include a YAML file that specifies what queries are available, along with
information to assist a frontend UI in obtaining user input and to present result sets back to the user.

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

There will be two new server endpoints:

1.  ``GET competency/queries`` will return a list of available
    queries giving their ``id``, ``label`` and ``description``.
2.  ``GET competency/queries/QUERY_ID`` will return details
    of a specific query (based on the above, in JSON).
3.  ``POST competency/query/`` will expect JSON data in the form::

        {
            "id": "QUERY_ID",
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
            "id": "QUERY_ID",
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
