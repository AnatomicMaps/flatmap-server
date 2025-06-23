import pytest
from utility import cq_request, assert_valid_query_response, SCKAN_VERSION, MALE_UUID

base_query = {
    'query_id': '21',
    'parameters': [
        {'column': 'feature_id','value': 'UBERON:0005453'}  # IMG
    ]
}

def test_sckan():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': SCKAN_VERSION}]}
    expected_rows = [
        [SCKAN_VERSION, '["ILX:0770759", ["UBERON:0001158"]]'],
        [SCKAN_VERSION, '["UBERON:0000483", ["UBERON:0001258"]]'],
        [SCKAN_VERSION, '["UBERON:0004243", []]']
    ]
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=3,
        expected_num_values=25,
        expected_rows=expected_rows
    )

def test_human_male_map():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': MALE_UUID}]}
    expected_rows = [
        [MALE_UUID, '["UBERON:0007177", ["UBERON:0001158"]]'],
        [MALE_UUID, '["UBERON:0000483", ["UBERON:0001258"]]'],
        [MALE_UUID, '["UBERON:0002367", []]'] # UBERON:0004243 is mapped to UBERON:0002367 in human-male map
    ]
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=3,
        expected_num_values=24,
        expected_rows=expected_rows
    )
