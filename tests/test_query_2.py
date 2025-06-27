import pytest
from utility import cq_request, assert_valid_query_response, SCKAN_VERSION

base_query = {
    'query_id': '2',
    'parameters': [
        {'column': 'feature_id', 'value': 'UBERON:0004713'}
    ]
}

def test_sckan():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': SCKAN_VERSION}]}
    response = cq_request(query)
    expected_path_ids = ['ilxtr:sparc-nlp/mmset4/3', 'ilxtr:sparc-nlp/mmset4/3a']
    expected_axon_terminals = ['["UBERON:0004713", []]']
    assert_valid_query_response(
        response,
        expected_num_keys=3,
        expected_num_values=2,
        expected_column_values={'path_id': expected_path_ids, 'axon_terminal': expected_axon_terminals}
    )
