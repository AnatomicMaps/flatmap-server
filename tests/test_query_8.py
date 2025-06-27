import pytest
from utility import cq_request, assert_valid_query_response, SCKAN_VERSION

base_query = {
    'query_id': '8',
    'parameters': [
        {'column': 'feature_id', 'value': 'ILX:0738324'}
    ]
}

def test_sckan():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': SCKAN_VERSION}]}
    expected_path_ids = ['ilxtr:neuron-type-bolew-unbranched-4']
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=2,
        expected_num_values=1,
        expected_column_values={'path_id': expected_path_ids}
    )
