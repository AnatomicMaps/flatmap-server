import pytest
from utility import cq_request, assert_valid_query_response

def test_sckan():
    query = {
        'query_id': '18',
        'parameters': [
            {'column': 'source_id','value': 'sckan-2024-09-21'},
            {
                'column': 'feature_id',
                'value': [
                    'UBERON:0006960',   # ovary stroma
                    'UBERON:0001190',   # ovarian artery
                    'UBERON:0001305',   # ovarian follicle
                    'UBERON:0002119',   # left ovary
                    'UBERON:0002118',   # right ovary
                    'UBERON:0000992'    # ovary
                ]
            }
        ]
    }
    expected_rows = [
        [
            'sckan-2024-09-21',
            'ilxtr:sparc-nlp/femrep/84',
            'ilxtr:sparc-nlp/femrep/94',
            '["ILX:0785238", []]',
            '["UBERON:0000992", []]', ['["ILX:0785238", []]', '["UBERON:0018675", []]', '["UBERON:0002014", []]', '["UBERON:0016508", []]', '["ILX:0793808", []]', '["UBERON:0011929", []]', '["UBERON:0000992", []]']
        ],
        [
            'sckan-2024-09-21',
            'ilxtr:sparc-nlp/mmset4/4b',
            'ilxtr:sparc-nlp/mmset4/5',
            '["UBERON:0001719", []]',
            '["UBERON:0000992", []]', ['["UBERON:0001719", []]', '["UBERON:0001759", []]', '["UBERON:0035772", []]', '["ILX:0794910", []]', '["ILX:0793832", []]', '["UBERON:0000992", []]']
        ]
    ]
    response = cq_request(query)
    assert_valid_query_response(
        response,
        expected_num_keys=6,
        expected_num_values=6,
        expected_rows=expected_rows
    )
