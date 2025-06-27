import pytest
from utility import cq_request, assert_valid_query_response, SCKAN_VERSION, MALE_UUID

base_query = {
    'query_id': '11',
    'parameters': [
        {'column': 'path_id', 'value': 'ilxtr:neuron-type-keast-4'}
    ]
}

def test_sckan():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': SCKAN_VERSION}]}
    expected_nerve_ids = [
        'ILX:0739299',
        'UBERON:0018675',
        'ILX:0793559',
        'ILX:0793228'
    ]
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=3,
        expected_num_values=4,
        expected_column_values={'nerve_id': expected_nerve_ids}
    )

def test_human_male_map():
    # ILX:0739299 (gray communicating ramus of sixth lumbar nerve) not expected in human
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': MALE_UUID}]}
    expected_nerve_ids = [
        'UBERON:0018675',
        'ILX:0793559',
        'ILX:0793228'
    ]
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=3,
        expected_num_values=3,
        expected_column_values={'nerve_id': expected_nerve_ids}
    )
