import pytest
from utility import cq_request, assert_valid_query_response, MALE_UUID, FEMALE_UUID, RAT_UUID, SCKAN_VERSION

base_query = {
    'query_id': '28',
    'parameters': [
        {'column': 'path_id','value': 'ilxtr:neuron-type-aacar-11'}
    ]
}

expected_expert_ids = ['https://orcid.org/0000-0001-9241-0864']

def test_sckan():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': SCKAN_VERSION}]}
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_column_values={'expert_id': expected_expert_ids}
    )

def test_human_male_map():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': MALE_UUID}]}
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_column_values={'expert_id': expected_expert_ids}
    )

def test_human_female_map():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': FEMALE_UUID}]}
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_column_values={'expert_id': expected_expert_ids}
    )

def test_human_rat_map():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': RAT_UUID}]}
    response = cq_request(query)
    print(MALE_UUID, response.json())
    assert_valid_query_response(
        response,
        expected_column_values={'expert_id': expected_expert_ids}
    )
