import pytest
from utility import cq_request, assert_valid_query_response, MALE_UUID, FEMALE_UUID, RAT_UUID

base_query = {
    'query_id': '30',
    'parameters': [
        {'column': 'feature_id', 'value': 'UBERON:0002080'}
    ]
}

human_expected_node_ids = [
    '["UBERON:0002165", ["UBERON:0002080"]]',
    '["UBERON:0002349", ["UBERON:0002080"]]'
]

def test_human_male_map():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': MALE_UUID}]}
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_column_values={'node_id': human_expected_node_ids}
    )

def test_human_female_map():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': FEMALE_UUID}]}
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_column_values={'node_id': human_expected_node_ids}
    )

def test_human_rat_map():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': RAT_UUID}]}
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_column_values={'node_id': human_expected_node_ids}
    )
