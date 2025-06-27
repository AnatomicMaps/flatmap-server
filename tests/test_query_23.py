import pytest
from utility import cq_request, assert_valid_query_response, SCKAN_VERSION, MALE_UUID

base_query = {
    'query_id': '23',
    'parameters': [
        {'column': 'path_id','value': 'ilxtr:neuron-type-keast-4'}
    ]
}

def test_sckan():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': SCKAN_VERSION}]}
    expected_rows = [
        [SCKAN_VERSION, 'ilxtr:neuron-type-keast-1'],
        [SCKAN_VERSION, 'ilxtr:neuron-type-keast-10']
    ]
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=2,
        expected_num_values=9,
        expected_rows=expected_rows
    )

def test_human_male_map():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': MALE_UUID}]}
    expected_rows = [
        [MALE_UUID, 'ilxtr:neuron-type-keast-1'],
        [MALE_UUID, 'ilxtr:neuron-type-keast-10'],
        [MALE_UUID, 'ilxtr:sparc-nlp/kidney/137']
    ]
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=2,
        expected_num_values=10,
        expected_rows=expected_rows
    )
