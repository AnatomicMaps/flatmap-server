import pytest
from utility import cq_request, assert_valid_query_response

def test_sckan():
    query = {
        'query_id': '1',
        'parameters': [
            {'column': 'feature_id', 'value': 'UBERON:0004713'},    # corpus cavernosum penis
            {'column': 'source_id', 'value': 'sckan-2024-09-21'}
        ]
    }
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
    query = {
        'query_id': '1',
        'parameters': [
            {'column': 'feature_id', 'value': 'UBERON:0004713'},
            {'column': 'source_id', 'value': '8fd48a4f-5323-5e37-aa99-3f03bd4d30d4'}    # human-flatmap_male
        ]
    }
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
    query = {
        'query_id': '1',
        'parameters': [
            {'column': 'feature_id', 'value': 'UBERON:0004713'},
            {'column': 'source_id', 'value': '456c7c6c-fb21-51f8-a878-4532f041aaa6'}    # human-flatmap_female
        ]
    }
    response = cq_request(query)
    expected_path_ids = []
    assert_valid_query_response(
        response,
        expected_num_keys=2,
        expected_num_values=0,
        expected_column_values={'path_id': expected_path_ids}
    )
