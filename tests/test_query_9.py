import pytest
from utility import cq_request, assert_valid_query_response, SCKAN_VERSION, MALE_UUID

base_query = {
    'query_id': '9',
    'parameters': [
        {'column': 'feature_id', 'value': 'UBERON:0001258'} # neck of urinary bladder
    ]
}

def test_sckan():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': SCKAN_VERSION}]}
    expected_nerve_ids = ['ILX:0793559']
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=3,
        expected_num_values=1,
        expected_column_values={'nerve_id': expected_nerve_ids}
    )

def test_human_male_map():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': MALE_UUID}]}
    expected_nerve_ids = ['ILX:0793559']
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=3,
        expected_num_values=1,
        expected_column_values={'nerve_id': expected_nerve_ids}
    )
