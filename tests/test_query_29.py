import pytest
from utility import cq_request, assert_valid_query_response, MALE_UUID, FEMALE_UUID, RAT_UUID, SCKAN_VERSION, CQ_END_POINT

base_query = {
    'query_id': '29',
    'parameters': [
        {'column': 'feature_id', 'value': 'UBERON:0002080'}
    ]
}

human_expected_path_ids = [
    'ilxtr:neuron-type-aacar-11',
    'ilxtr:neuron-type-aacar-6',
    'ilxtr:neuron-type-aacar-7v',
    'ilxtr:neuron-type-aacar-8v',
    'ilxtr:neuron-type-aacar-9v'
]

rat_expected_node_ids = human_expected_path_ids + [
        'ilxtr:neuron-type-aacar-13'
    ]

def test_human_male_map():

    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': MALE_UUID}]}
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_column_values={'path_id': human_expected_path_ids}
    )

def test_human_female_map():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': FEMALE_UUID}]}
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_column_values={'path_id': human_expected_path_ids}
    )

def test_human_rat_map():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': RAT_UUID}]}
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_column_values={'path_id': rat_expected_node_ids}
    )
