import requests
from tools.portal_maps import ENDPOINTS, latest_maps

END_POINT = ENDPOINTS['development']
CQ_END_POINT = f'{END_POINT}/competency/query'
HEADERS = {'Content-Type': 'application/json'}

# latest flatmap UUIDs for testing obtained dynamically
maps = latest_maps(END_POINT)

MALE_KEY = ('NCBITaxon:9606', 'PATO:0000384')
FEMALE_KEY = ('NCBITaxon:9606', 'PATO:0000383')
RAT_KEY = ('NCBITaxon:10114', None)

MALE_FALLBACK_UUID = '2b76d336-5c56-55e3-ab1e-795d6c63f9c1'
FEMALE_FALLBACK_UUID = '91359a0f-9e32-5309-b365-145d9956817d'
RAT_FALLBACK_UUID = 'fb6d0345-cb70-5c7e-893c-d744a6313c95'

MALE_UUID = maps.get(MALE_KEY, {}).get('uuid', MALE_FALLBACK_UUID)
FEMALE_UUID = maps.get(FEMALE_KEY, {}).get('uuid', FEMALE_FALLBACK_UUID)
RAT_UUID = maps.get(RAT_KEY, {}).get('uuid', RAT_FALLBACK_UUID)

SCKAN_VERSION = 'sckan-2026-02-11'

def cq_request(query: dict):
    response = requests.post(CQ_END_POINT, json=query, headers=HEADERS)
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
            actual_values = [
                tuple(row[idx]) if isinstance(row[idx], list) else row[idx]
                for row in values
            ]
            expected_values = [
                tuple(value) if isinstance(value, list) else value
                for value in expected_values
            ]
            assert set(actual_values) == set(expected_values), (
                f"Expected values in column '{col}' to be {expected_values}, but got {actual_values}"
            )

    if expected_rows:
        for row in expected_rows:
            assert any(
                all(item in value for item in row) for value in values
            ), f"Missing expected row: {row}"
