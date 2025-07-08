import pytest
from utility import cq_request, assert_valid_query_response, SCKAN_VERSION

base_query = {
    'query_id': '17',
    'parameters': [
        {'column': 'taxon_id', 'value': ['NCBITaxon:9606', 'NCBITaxon:10116']},
        {
            'column': 'feature_id',
            'value': [
                'UBERON:0001255',   # urinary bladder
                'UBERON:0004228',   # urinary bladder smooth muscle
                'UBERON:0001256',   # wall of urinary bladder
                'UBERON:0001258',   # neck of urinary bladder
                'UBERON:0002068',   # urachus
                'UBERON:0006082',   # fundus of urinary bladder
                'UBERON:0009958',   # bladder lumen
                'UBERON:0012239',   # urinary bladder vasculature
                'ILX:0793663',      # Arteriole in connective tissue of bladder neck
                'ILX:0793664',      # Arteriole in connective tissue of bladder dome
                'UBERON:0001258'    # neck of urinary bladder
            ]
        }
    ]
}

def test_sckan():
    query = {**base_query, 'parameters': base_query['parameters'] + [{'column': 'source_id', 'value': SCKAN_VERSION}]}
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=4,
        expected_num_values=188
    )
