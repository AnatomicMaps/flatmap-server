import pytest
import requests

endpoint = "https://mapcore-demo.org/devel/flatmap/v4/competency/query"
headers = {"Content-Type": "application/json"}

queries = [
    (
        'query_1',
        {
            'query_id': '1',
            'parameters': [
                {'column': 'feature_id', 'value': 'UBERON:0004713'},
                {'column': 'source_id', 'value': 'sckan-2024-09-21'}
            ]
        },
        2,  # expected keys
        2   # expected values
    ),
    (
        'query_2',
        {
            'query_id': '2',
            'parameters': [
                {'column': 'feature_id', 'value': 'UBERON:0004713'},
                {'column': 'source_id', 'value': 'sckan-2024-09-21'}
            ]
        },
        3,
        2
    ),
    (
        'query_3',
        {
            'query_id': '3',
            'parameters': [
                {'column': 'evidence_id', 'value': 'http://www.ncbi.nlm.nih.gov/pubmed/27783854'},
                {'column': 'source_id','value': 'sckan-2024-09-21'}
            ]
        },
        2,
        3
    ),
    (
        'query_4',
        {
            'query_id': '4',
            'parameters': [
                {'column': 'path_id', 'value': 'ilxtr:neuron-type-aacar-11'},
                {'column': 'taxon_id', 'value': 'NCBITaxon:9615'},
                {'column': 'source_id', 'value': 'sckan-2024-09-21'}
            ]
        },
        2,
        1
    ),
    (
        'query_5',
        {
            'query_id': '5',
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
                },
                {'column': 'source_id','value': 'sckan-2024-09-21'}
            ]
        },
        8,
        9
    ),
    (
        'query_6',
        {
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
                },
                {'column': 'source_id', 'value': 'sckan-2024-09-21'}
            ]
        },
        8,
        6
    ),
    (
        'query_7',
        {
            'query_id': '7',
            'parameters': [
                {
                    'column': 'feature_id_0',
                    'value': [
                        'ILX:0738326',     # wall of larynx
                        'UBERON:0001737'   # larynx
                    ]
                },
                {
                    'column': 'feature_id_1',
                    'value': [
                        'UBERON:0004982',   # mucosa of epiglottis
                        'UBERON:0000388'    # epiglottis
                    ]
                },
                {'column': 'source_id','value': 'sckan-2024-09-21'}
            ]
        },
        8,
        8
    ),
    (
        'query_8',
        {
            'query_id': '8',
            'parameters': [
                {'column': 'feature_id', 'value': 'ILX:0738324'},
                {'column': 'source_id', 'value': 'sckan-2024-09-21'}
            ]
        },
        2,
        1
    ),
    (
        'query_9',
        {
            'query_id': '9',
            'parameters': [
                {'column': 'feature_id', 'value': 'UBERON:0001258'},   # neck of urinary bladder
                {'column': 'source_id','value': 'sckan-2024-09-21'}
            ]
        },
        3,
        1
    ),
    (
        'query_10',
        {
            'query_id': '10',
            'parameters': [
                {'column': 'feature_id', 'value': 'UBERON:0001258'},   # neck of urinary bladder
                {'column': 'source_id','value': 'sckan-2024-09-21'}
            ]
        },
        3,
        7
    ),
    (
        'query_11',
        {
            'query_id': '11',
            'parameters': [
                {'column': 'path_id', 'value': 'ilxtr:neuron-type-keast-4'},
                {'column': 'source_id','value': 'sckan-2024-09-21'}
            ]
        },
        3,
        4
    ),
    (
        'query_12',
        {
            'query_id': '12',
            'parameters': [
                {'column': 'source_id','value': 'sckan-2024-09-21'}
            ],
            'order': ['nerve_id']
        },
        4,
        409
    ),
    (
        'query_13',
        {
            'query_id': '13',
            'parameters': [
                {'column': 'feature_id', 'value': 'ILX:0793559'},   # bladder nerve
                {'column': 'source_id','value': 'sckan-2024-09-21'}
            ]
        },
        2,
        5
    ),
    (
        'query_14',
        {
            'query_id': '14',
            'parameters': [
                {'column': 'feature_id', 'value': 'ILX:0793559'},   # bladder nerve
                {'column': 'source_id','value': 'sckan-2024-09-21'}
            ]
        },
        2,
        22
    ),
    (
        'query_15',
        {
            'query_id': '15',
            'parameters': [
                {'column': 'feature_id', 'value': 'ILX:0793559'},   # bladder nerve
                {'column': 'source_id','value': 'sckan-2024-09-21'}
            ]
        },
        3,
        43
    ),
    (
        'query_16',
        {
            'query_id': '16',
            'parameters': [
                {'column': 'taxon_id', 'value': ['NCBITaxon:9606', 'NCBITaxon:10116']},
                {'column': 'source_id','value': 'sckan-2024-09-21'}
            ]
        },
        3,
        354
    ),
    (
        'query_17',
        {
            'query_id': '17',
            'parameters': [
                {'column': 'taxon_id', 'value': ['NCBITaxon:9606', 'NCBITaxon:10116']},
                {'column': 'source_id','value': 'sckan-2024-09-21'},
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
        },
        4,
        188
    ),
    (
        'query_18',
        {
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
        },
        6,
        6
    ),
    (
        'query_19',
        {
            'query_id': '19',
            'parameters': [
                {'column': 'source_id','value': 'sckan-2024-09-21'},
                {
                    'column': 'feature_id',
                    'value': [
                        'UBERON:0002078', # right atrium
                        'UBERON:0002078', # left atrium
                        'UBERON:0002080', # heart right ventricle
                        'UBERON:0002084', # left ventricle
                        'UBERON:0000948'  # heart
                    ]
                }
            ]
        },
        6,
        3780
    ),
    (
        'query_20',
        {
            'query_id': '20',
            'parameters': [
                {'column': 'source_id', 'value': 'sckan-2024-09-21'},
                {'column': 'feature_id','value': 'UBERON:0005453'}  # IMG
            ]
        },
        3,
        71
    ),
    (
        'query_21',
        {
            'query_id': '21',
            'parameters': [
                {'column': 'source_id', 'value': 'sckan-2024-09-21'},
                {'column': 'feature_id','value': 'UBERON:0005453'}  # IMG
            ]
        },
        3,
        25
    ),
    (
        'query_22',
        {
            'query_id': '22',
            'parameters': [
                {'column': 'source_id', 'value': 'sckan-2024-09-21'},
                {'column': 'path_id','value': 'ilxtr:neuron-type-keast-4'}
            ]
        },
        2,
        20
    ),
    (
        'query_23',
        {
            'query_id': '23',
            'parameters': [
                {'column': 'source_id', 'value': 'sckan-2024-09-21'},
                {'column': 'path_id','value': 'ilxtr:neuron-type-keast-4'}
            ]
        },
        2,
        9
    )
]

def post_request(query):
    response = requests.post(endpoint, json=query, headers=headers)
    return response

@pytest.mark.parametrize("query_name, query, expected_keys, expected_values", queries, ids=[q[0] for q in queries])
def test_query_outputs(query_name, query, expected_keys, expected_values):
    response = post_request(query)
    assert response.status_code in (200, 201), f"{query_name} failed with status {response.status_code}"

    json_response = response.json()
    results = json_response.get('results', {})

    assert 'keys' in results, f"{query_name} missing 'keys'"
    assert 'values' in results, f"{query_name} missing 'values'"

    assert len(results['keys']) == expected_keys, f"{query_name} has {len(results['keys'])} keys, expected {expected_keys}"
    assert len(results['values']) == expected_values, f"{query_name} has {len(results['values'])} values, expected {expected_values}"
