import pytest
from utility import cq_request, assert_valid_query_response, SCKAN_VERSION, RAT_UUID

base_query = {
    'query_id': '19',
    'parameters': [
        {'column': 'feature_id', 'value': 'UBERON:0002078'} # right atrium
    ]
}

def test_sckan():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': SCKAN_VERSION}]}
    expected_path_ids = ['ilxtr:neuron-type-aacar-5']
    expected_forward_path_ids = ['ilxtr:neuron-type-aacar-6', 'ilxtr:neuron-type-aacar-8a']
    expected_rows = [
        [
            SCKAN_VERSION,
            'ilxtr:neuron-type-aacar-5',
            'ilxtr:neuron-type-aacar-6',
            '["UBERON:0006452", []]',
            '["UBERON:0002165", ["UBERON:0002078"]]', ['["UBERON:0006452", []]', '["ILX:0792838", []]', '["ILX:0793210", []]', '["ILX:0786272", []]', '["ILX:0739241", []]', '["ILX:0793550", []]', '["UBERON:0015129", ["UBERON:0000948"]]', '["UBERON:0002348", ["UBERON:0000948"]]', '["UBERON:0002349", ["UBERON:0002078"]]', '["UBERON:0002165", ["UBERON:0002078"]]']
        ]
    ]
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=6,
        expected_num_values=1068,
        expected_column_values={'path_id': expected_path_ids, 'forward_path_id': expected_forward_path_ids},
        expected_rows=expected_rows
    )

def test_rat_map():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': RAT_UUID}]}
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=6,
        expected_num_values=0   # Note: 'ilxtr:neuron-type-aacar-5' omitted due to disconnected paths, hence zero results
    )
