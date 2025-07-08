import pytest
from utility import cq_request, assert_valid_query_response, SCKAN_VERSION

base_query = {
    'query_id': '6',
    'parameters': [
        {
            'column': 'feature_id_0',
            'value': [
                'UBERON:0002048',   # lung
                'UBERON:0002185',   # bronchus
                'UBERON:0002186',   # bronchiole
                'UBERON:0002187',   # terminal bronchiole
                'UBERON:0004515',   # smooth muscle tissue of bronchiole
                'UBERON:0004516',   # smooth muscle tissue of terminal bronchiole
                'ILX:0793764',      # Wall of bronchus
                'ILX:0793765',      # Wall of bronchiole
                'ILX:0775392',      # Wall of terminal bronchiole
                'ILX:0793571',      # bronchus parasympathetic ganglia
                'ILX:0793572',      # bronchiole parasympathetic ganglia
                'ILX:0793573'       # terminal bronchiole parasympathetic ganglia
            ]
        },
        {
            'column': 'feature_id_1',
            'value': [
                'UBERON:0000948',   # heart
                'UBERON:0002078',   # right atrium
                'UBERON:0002079',   # left atrium
                'UBERON:0002080',   # heart right ventricle
                'UBERON:0002084',   # left ventricle
                'UBERON:0003379',   # cardiac muscle of right atrium
                'UBERON:0003380',   # cardiac muscle of left atrium
                'UBERON:0003381',   # cardiac muscle of right ventricle
                'UBERON:0003382',   # cardiac muscle of left ventricle
                'UBERON:0002165',   # endocardium
                'UBERON:0002349',   # myocardium
                'UBERON:0002348',   # epicardium
                'ILX:0793555',      # Atrial intrinsic cardiac ganglion
                'ILX:0793556'       # ventricular intrinsic cardiac ganglion
            ]
        }
    ]
}

def test_sckan():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': SCKAN_VERSION}]}
    expected_shared_somas = ['["UBERON:0001719", []]']
    expected_connected_paths_0 = [
        ['ilxtr:neuron-type-bromo-2', 'ilxtr:neuron-type-bromo-4'],
        ['ilxtr:neuron-type-bromo-2', 'ilxtr:neuron-type-bromo-5'],
        ['ilxtr:neuron-type-bromo-2', 'ilxtr:neuron-type-bromo-6']
    ]
    expected_connected_paths_1 = [
        ['ilxtr:neuron-type-aacar-4', 'ilxtr:neuron-type-aacar-7a'],
        ['ilxtr:neuron-type-aacar-4', 'ilxtr:neuron-type-aacar-7v']
        # Note: ['ilxtr:neuron-type-aacar-4', 'ilxtr:neuron-type-aacar-10a'] is omitted
        #        because 'ilxtr:neuron-type-aacar-10a' is not parasympathetic.
    ]
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=8,
        expected_num_values=6,
        expected_column_values={
            'soma': expected_shared_somas,
            'connected_paths_0': expected_connected_paths_0,
            'connected_paths_1': expected_connected_paths_1
        }
    )
