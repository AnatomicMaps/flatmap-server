import pytest
from utility import cq_request, assert_valid_query_response, SCKAN_VERSION, MALE_UUID, FEMALE_UUID, RAT_UUID

base_query = {
    'query_id': '26',
    'parameters': [
        {'column': 'path_id','value': 'ilxtr:neuron-type-sstom-4'}
    ]
}

base_query_expected_path_ids = [
    'ilxtr:neuron-type-sstom-1',
    'ilxtr:neuron-type-sstom-2',
    'ilxtr:neuron-type-sstom-3',
    'ilxtr:neuron-type-sstom-5'
]

backward_query = {
    'query_id': '26',
    'parameters': [
        {'column': 'path_id','value': 'ilxtr:neuron-type-sstom-12'}
    ]
}

backward_query_expected_path_ids = [
    'ilxtr:neuron-type-sstom-6',
    'ilxtr:neuron-type-sstom-5',
    'ilxtr:neuron-type-sstom-8'
]

def test_sckan():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': SCKAN_VERSION}]}
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=4,
        expected_num_values=4,
        expected_column_values={'dest_path_id': base_query_expected_path_ids}
    )

    query = {**backward_query, 'parameters': backward_query['parameters'] + [{'column': 'source_id', 'value': SCKAN_VERSION}]}
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=4,
        expected_num_values=3,
        expected_column_values={'dest_path_id': backward_query_expected_path_ids}
    )

def test_human_male_map():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': MALE_UUID}]}
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=4,
        expected_num_values=4,
        expected_column_values={'dest_path_id': base_query_expected_path_ids}
    )

    query = {**backward_query, 'parameters': backward_query['parameters'] + [{'column': 'source_id', 'value': MALE_UUID}]}
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=4,
        expected_num_values=3,
        expected_column_values={'dest_path_id': backward_query_expected_path_ids}
    )

def test_human_female_map():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': FEMALE_UUID}]}
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=4,
        expected_num_values=4,
        expected_column_values={'dest_path_id': base_query_expected_path_ids}
    )

    query = {**backward_query, 'parameters': backward_query['parameters'] + [{'column': 'source_id', 'value': FEMALE_UUID}]}
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=4,
        expected_num_values=3,
        expected_column_values={'dest_path_id': backward_query_expected_path_ids}
    )

def test_human_rat_map():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': RAT_UUID}]}
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=4,
        expected_num_values=4,
        expected_column_values={'dest_path_id': base_query_expected_path_ids}
    )

    query = {**backward_query, 'parameters': backward_query['parameters'] + [{'column': 'source_id', 'value': RAT_UUID}]}
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=4,
        expected_num_values=3,
        expected_column_values={'dest_path_id': backward_query_expected_path_ids}
    )
