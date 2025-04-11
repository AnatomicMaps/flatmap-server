Competency Queries
==================

Flatmap rendered connectivity
-----------------------------

1.  All connectivity related Postgres tables have a ``source`` column.
2.  This column could hold a map UUID instead of a SCKAN release tag.
3.  Then rendered connectivity can be easily held in Postgres for published maps.
4.  Need a utility to load knowledge from published maps.
5.  This could also update a new ``published-flatmaps`` table with the map’s knowledge source, taxon, and biological sex.


Query descriptions
------------------

A JSON file, ``competency.json``::

    {
        "queries": [
            {
                "id": "QUERY_ID",
                "label": "A short label",
                "description": "What this query is all about...",
                "sql": "SQL query with placeholders for parameters",
                "parameters": [
                    {
                        "id": "PARAM_ID",
                        "label": "Human readable label",
                        "type": "number", ## "string", "boolean", "choice"
                        "choices": {      ## Only when type is "choice"
                            "id": "CHOICE_ID",
                            "label": "Human readable label"
                        }
                    },
                    {
                        .
                        .
                    }
                ],
                "results": [
                    {
                        "id": "RESULT_ID",
                        "label": "Human readable label",
                        "type": "number" ## "string", "boolean"
                    },
                    {
                        .
                        .
                    }

                ]
            },
            {
                .
                .
                .
            }
        ]
    }

Server endpoints
----------------

*   ``GET competency/queries`` will return the above JSON.

*   ``POST competency/query/`` with JSON data in the form::

        {
            "id": "QUERY_ID",
            "parameters": [
                {
                    "id": "PARAM_ID",
                    "value": "Parameter value"
                },
                {
                    .
                    .
                }
            ]
        }


will return as JSON::

        {
            "id": "QUERY_ID",
            "results": [
                {
                    "id": "RESULT_ID",
                    "value": "Result value"
                },
                {
                    .
                    .
                }
            ]
        }
