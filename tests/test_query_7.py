import pytest
from utility import cq_request, assert_valid_query_response, SCKAN_VERSION

base_query = {
    'query_id': '7',
    'parameters': [
        {
            'column': 'feature_id_0',
            'value': [
                'ILX:0738326',     # wall of larynx
                'UBERON:0001737'   # larynx
            ]
        },
        {
            'column': 'feature_id_1',
            'value': [
                'UBERON:0004982',   # mucosa of epiglottis
                'UBERON:0000388'    # epiglottis
            ]
        }
    ]
}

def test_sckan():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': SCKAN_VERSION}]}
    expected_shared_somas = ['["UBERON:0006457", []]']
    expected_connected_paths_0 = [
        ['ilxtr:neuron-type-bolew-unbranched-2', 'ilxtr:neuron-type-bolew-unbranched-16'],
        ['ilxtr:neuron-type-bolew-unbranched-2', 'ilxtr:neuron-type-bolew-unbranched-17']
    ]
    expected_connected_paths_1 = [
        ['ilxtr:neuron-type-bolew-unbranched-2', 'ilxtr:neuron-type-bolew-unbranched-18'],
        ['ilxtr:neuron-type-bolew-unbranched-2', 'ilxtr:neuron-type-bolew-unbranched-19'],
        ['ilxtr:neuron-type-bolew-unbranched-2', 'ilxtr:neuron-type-bolew-unbranched-20'],
        ['ilxtr:neuron-type-bolew-unbranched-2', 'ilxtr:neuron-type-bolew-unbranched-21']
    ]
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=8,
        expected_num_values=8,
        expected_column_values={
            'soma': expected_shared_somas,
            'connected_paths_0': expected_connected_paths_0,
            'connected_paths_1': expected_connected_paths_1
        }
    )
