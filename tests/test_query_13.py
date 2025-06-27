import pytest
from utility import cq_request, assert_valid_query_response, SCKAN_VERSION

base_query = {
    'query_id': '13',
    'parameters': [
        {'column': 'feature_id', 'value': 'ILX:0793559'}    # bladder nerve
    ]
}

def test_sckan():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': SCKAN_VERSION}]}
    expected_axon_terminals = [
        '["UBERON:0000483", ["UBERON:0001258"]]',
        '["UBERON:0001135", ["UBERON:0001258"]]',
        '["UBERON:0002384", ["UBERON:0001258"]]',
        '["UBERON:0035965", ["ILX:0793663"]]',
        '["UBERON:0035965", ["ILX:0793664"]]'
    ]
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=2,
        expected_num_values=5,
        expected_column_values={'axon_terminal': expected_axon_terminals}
    )
