Competency Queries via a Flatmap Server
=======================================

Query descriptions
------------------

A server's configuration will include a file that specifies what queries are available, along with
information to assist a frontend UI in obtaining user input and to present result sets back to the user.

::

    {
        "queries": [
            {
                "id": "QUERY_ID",
                "label": "A short label",
                "description": "What this query is all about...",
                "sql": "SQL query with named placeholders for parameters, e.g. ... WHERE col=%(PARAM_ID)s",
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

There will be two new server endpoints:

1.  ``GET competency/queries`` will return the above JSON.

2.  ``POST competency/query/`` will expect JSON data in the form::

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


    and returns::

        {
            "id": "QUERY_ID",
            "results": {
                "keys": ["RESULT_ID", ...],
                "values": [
                    ["First result row, RESULT_ID value", ...],
                    ["Second result row, RESULT_ID value", ...],
                        .
                        .
                        .
                ]
            }
        }
