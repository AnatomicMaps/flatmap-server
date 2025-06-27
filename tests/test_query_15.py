import pytest
from utility import cq_request, assert_valid_query_response, SCKAN_VERSION

base_query = {
    'query_id': '15',
    'parameters': [
        {'column': 'feature_id', 'value': 'ILX:0793559'}    # bladder nerve
    ]
}

def test_sckan():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': SCKAN_VERSION}]}
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=3,
        expected_num_values=43
    )
