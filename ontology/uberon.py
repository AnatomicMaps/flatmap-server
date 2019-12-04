import json
import owlready2 as owl


uberon = owl.get_ontology('./uberon.owl').load()
## 'http://purl.obolibrary.org/obo/uberon.owl'

obo = uberon.get_namespace("http://purl.obolibrary.org/obo/")

summary = {}
for c in uberon.classes():
    if c.name.startswith('UBERON_'):
        is_a = []
        part_of = []
        for part in c.is_a:
            if (isinstance(part, owl.entity.ThingClass)
              and part.name.startswith('UBERON_')):
                is_a.append(part.name)
            elif (isinstance(part, owl.class_construct.Restriction)
              and part.property == obo.BFO_0000050
              and part.value.name.startswith('UBERON_')):
                part_of.append(part.value.name)
        summary[c.name] = { 'is_a': is_a,
                            'label': c.label,
                            'part_of': part_of,
                          }

with open('uberon.json', 'w') as fp:
    json.dump(summary, fp, indent=4)
