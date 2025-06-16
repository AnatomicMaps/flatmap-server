import pytest
from utility import cq_request, assert_valid_query_response

def test_sckan():
    query = {
        'query_id': '3',
        'parameters': [
            {'column': 'evidence_id', 'value': 'http://www.ncbi.nlm.nih.gov/pubmed/27783854'},
            {'column': 'source_id', 'value': 'sckan-2024-09-21'}
        ]
    }
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
    query = {
        'query_id': '3',
        'parameters': [
            {'column': 'evidence_id', 'value': 'http://www.ncbi.nlm.nih.gov/pubmed/27783854'},
            {'column': 'source_id', 'value': '70667915-27db-5d32-90c2-f6e221f5b4aa'}
        ]
    }
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
