import pytest
from utility import cq_request, assert_valid_query_response, SCKAN_VERSION, RAT_UUID

def test_sckan():
    # test query with complete source, via, and destination nodes
    query = {
        'query_id': '24',
        'parameters': [
            {'column': 'source_id', 'value': SCKAN_VERSION},
            {'column': 'source_node_id', 'value': ['["ILX:0787009", []]']},                 # twelfth thoracic ganglion
            {'column': 'via_node_id', 'value': ['["ILX:0793559", []]']},                    # bladder nerve
            {'column': 'dest_node_id', 'value': ['["UBERON:0035965", ["ILX:0793664"]]']}    # wall of blood vessel/arteriole in connective tissue of bladder dome
        ]
    }
    response = cq_request(query)
    expected_path_ids = ['ilxtr:neuron-type-keast-4']
    assert_valid_query_response(
        response,
        expected_num_keys=2,
        expected_num_values=1,
        expected_column_values={'path_id': expected_path_ids}
    )

    # test query with source and destination nodes only
    query = {
        'query_id': '24',
        'parameters': [
            {'column': 'source_id', 'value': SCKAN_VERSION},
            {'column': 'source_node_id', 'value': ['["ILX:0787009", []]']},                 # twelfth thoracic ganglion
            {'column': 'dest_node_id', 'value': ['["UBERON:0035965", ["ILX:0793664"]]']}    # wall of blood vessel/arteriole in connective tissue of bladder dome
        ]
    }
    response = cq_request(query)
    expected_path_ids = ['ilxtr:neuron-type-keast-4']
    assert_valid_query_response(
        response,
        expected_num_keys=2,
        expected_num_values=1,
        expected_column_values={'path_id': expected_path_ids}
    )

    # test query with via nodes only
    query = {
        'query_id': '24',
        'parameters': [
            {'column': 'source_id', 'value': SCKAN_VERSION},
            {'column': 'via_node_id', 'value': ['["ILX:0793559", []]']},                    # bladder nerve
        ]
    }
    response = cq_request(query)
    expected_path_ids = [
        'ilxtr:neuron-type-keast-1',
        'ilxtr:neuron-type-keast-10',
        'ilxtr:neuron-type-keast-11',
        'ilxtr:neuron-type-keast-2',
        'ilxtr:neuron-type-keast-3',
        'ilxtr:neuron-type-keast-4'
    ]
    assert_valid_query_response(
        response,
        expected_num_keys=2,
        expected_num_values=6,
        expected_column_values={'path_id': expected_path_ids}
    )

    # test query with destination nodes only
    query = {
        'query_id': '24',
        'parameters': [
            {'column': 'source_id', 'value': SCKAN_VERSION},
            {'column': 'dest_node_id', 'value': ['["UBERON:0005020", ["UBERON:0001723"]]']} # mucosa of tongue/tongue
        ]
    }
    response = cq_request(query)
    expected_path_ids = [
        'ilxtr:neuron-type-bolew-unbranched-22',
        'ilxtr:neuron-type-bolew-unbranched-23'
    ]
    assert_valid_query_response(
        response,
        expected_num_keys=2,
        expected_num_values=2,
        expected_column_values={'path_id': expected_path_ids}
    )

def test_rat_map():
    # test query with complete source, via, and destination nodes
    query = {
        'query_id': '24',
        'parameters': [
            {'column': 'source_id', 'value': RAT_UUID},
            {'column': 'source_node_id', 'value': ['["ILX:0787009", []]']},                 # twelfth thoracic ganglion
            {'column': 'via_node_id', 'value': ['["ILX:0793559", []]']},                    # bladder nerve
            {'column': 'dest_node_id', 'value': ['["UBERON:0035965", ["UBERON:0006082"]]']} # wall of blood vessel/fundus of urinary bladder
        ]
    }
    response = cq_request(query)
    expected_path_ids = ['ilxtr:neuron-type-keast-4']
    assert_valid_query_response(
        response,
        expected_num_keys=2,
        expected_num_values=1,
        expected_column_values={'path_id': expected_path_ids}
    )

    # test query with source and destination nodes only
    query = {
        'query_id': '24',
        'parameters': [
            {'column': 'source_id', 'value': RAT_UUID},
            {'column': 'source_node_id', 'value': ['["ILX:0787009", []]']},                 # twelfth thoracic ganglion
            {'column': 'dest_node_id', 'value': ['["UBERON:0035965", ["UBERON:0006082"]]']} # wall of blood vessel/fundus of urinary bladder
        ]
    }
    response = cq_request(query)
    expected_path_ids = ['ilxtr:neuron-type-keast-4']
    assert_valid_query_response(
        response,
        expected_num_keys=2,
        expected_num_values=1,
        expected_column_values={'path_id': expected_path_ids}
    )

     # test query with via nodes only
    query = {
        'query_id': '24',
        'parameters': [
            {'column': 'source_id', 'value': RAT_UUID},
            {'column': 'via_node_id', 'value': ['["ILX:0793559", []]']},                    # bladder nerve
        ]
    }
    response = cq_request(query)
    expected_path_ids = [
        'ilxtr:neuron-type-keast-1',
        'ilxtr:neuron-type-keast-10',
        'ilxtr:neuron-type-keast-11',
        'ilxtr:neuron-type-keast-2',
        'ilxtr:neuron-type-keast-3',
        'ilxtr:neuron-type-keast-4'
    ]
    assert_valid_query_response(
        response,
        expected_num_keys=2,
        expected_num_values=6,
        expected_column_values={'path_id': expected_path_ids}
    )
