import pytest
from utility import cq_request, assert_valid_query_response, SCKAN_VERSION, RAT_UUID

base_query = {
    'query_id': '3',
    'parameters': [
        {'column': 'evidence_id', 'value': 'http://www.ncbi.nlm.nih.gov/pubmed/27783854'}
    ]
}

def test_sckan():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': SCKAN_VERSION}]}
    expected_path_ids = [
        'ilxtr:neuron-type-aacar-11',
        'ilxtr:neuron-type-aacar-13',
        'ilxtr:neuron-type-aacar-5'
    ]
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=2,
        expected_num_values=3,
        expected_column_values={'path_id': expected_path_ids}
    )

def test_rat_map():
    # Note: 'ilxtr:neuron-type-aacar-5' omitted due to disconnected paths
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': RAT_UUID}]}
    expected_path_ids = [
        'ilxtr:neuron-type-aacar-11',
        'ilxtr:neuron-type-aacar-13'
    ]
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=2,
        expected_num_values=2,
        expected_column_values={'path_id': expected_path_ids}
    )
