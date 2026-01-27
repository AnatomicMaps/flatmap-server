import pytest
from utility import cq_request, assert_valid_query_response, MALE_UUID, FEMALE_UUID, RAT_UUID

base_query = {
    'query_id': '27',
    'parameters': [
        {'column': 'path_id','value': 'ilxtr:neuron-type-bolew-unbranched-15'}
    ]
}

expected_sckan_node_ids = [
    '["ILX:0738293", []]',
    '["ILX:0738305", ["UBERON:0001532"]]',
    '["ILX:0793621", []]',
    '["UBERON:0001989", []]',
    '["UBERON:0003708", []]'
]
expected_node_ids = [
    '["ILX:0738293", []]',
    '["ILX:0738305", []]',
    '["ILX:0793621", []]',
    '["UBERON:0001989", []]',
    '["UBERON:0003708", []]'
]

def test_human_male_map():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': MALE_UUID}]}
    response = cq_request(query)

    assert_valid_query_response(
        response,
        expected_num_keys=7,
        expected_num_values=5,
        expected_column_values={
            'sckan_node_id': expected_sckan_node_ids,
            'node_id': expected_node_ids
        }
    )

def test_human_female_map():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': FEMALE_UUID}]}
    response = cq_request(query)

    assert_valid_query_response(
        response,
        expected_num_keys=7,
        expected_num_values=5,
        expected_column_values={
            'sckan_node_id': expected_sckan_node_ids,
            'node_id': expected_node_ids
        }
    )

def test_human_rat_map():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': RAT_UUID}]}
    response = cq_request(query)

    assert_valid_query_response(
        response,
        expected_num_keys=7,
        expected_num_values=5,
        expected_column_values={
            'sckan_node_id': expected_sckan_node_ids,
            'node_id': expected_node_ids
        }
    )
#===============================================================================
