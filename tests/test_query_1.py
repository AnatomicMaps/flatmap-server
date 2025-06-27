import pytest
from utility import cq_request, assert_valid_query_response, SCKAN_VERSION, MALE_UUID, FEMALE_UUID

base_query = {
    'query_id': '1',
    'parameters': [
        {'column': 'feature_id', 'value': 'UBERON:0004713'} # corpus cavernosum penis
    ]
}

def test_sckan():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': SCKAN_VERSION}]}
    response = cq_request(query)
    expected_path_ids = ['ilxtr:sparc-nlp/mmset4/3', 'ilxtr:sparc-nlp/mmset4/3a']
    assert_valid_query_response(
        response,
        expected_num_keys=2,
        expected_num_values=2,
        expected_column_values={'path_id': expected_path_ids}
    )

def test_human_male_map():
    # Note: 'ilxtr:sparc-nlp/mmset4/3a' having MPG as soma in rat, not expected in human
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': MALE_UUID}]}
    response = cq_request(query)
    expected_path_ids = ['ilxtr:sparc-nlp/mmset4/3']
    assert_valid_query_response(
        response,
        expected_num_keys=2,
        expected_num_values=1,
        expected_column_values={'path_id': expected_path_ids}
    )

def test_human_female_map():
    # corpus cavernosum penis not expected in female
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': FEMALE_UUID}]}
    response = cq_request(query)
    expected_path_ids = []
    assert_valid_query_response(
        response,
        expected_num_keys=2,
        expected_num_values=0,
        expected_column_values={'path_id': expected_path_ids}
    )
