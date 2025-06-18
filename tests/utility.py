import requests

END_POINT = 'https://mapcore-demo.org/devel/flatmap/v4/competency/query'
HEADERS = {'Content-Type': 'application/json'}

def cq_request(query: dict):
    response = requests.post(END_POINT, json=query, headers=HEADERS)
    return response

def assert_valid_query_response(
        response,
        expected_num_keys=None,
        expected_num_values=None,
        expected_column_values=None,
        expected_rows=None
    ):
    assert response.status_code in (200, 201), f'Unexpected status code: {response.status_code}'
    json_response = response.json()

    results = json_response.get('results', {})
    keys = results.get('keys', [])
    values = results.get('values', [])

    if expected_num_keys:
        assert len(keys) == expected_num_keys, f"Expected {expected_num_keys} keys but got {len(keys)}"

    if expected_num_values:
        assert len(values) == expected_num_values, f"Expected {expected_num_values} value rows but got {len(values)}"

    if expected_column_values:
        for col, expected_values in expected_column_values.items():
            assert col in keys, f"Column '{col}' not found in result keys"
            idx = keys.index(col)
            actual_values = [row[idx] for row in values]
            assert set(actual_values) == set(expected_values), (
                f"Expected values in column '{col}' to be {expected_values}, but got {actual_values}"
            )

    if expected_rows:
        for row in expected_rows:
            assert row in values, f"Missing expected row: {row}"
