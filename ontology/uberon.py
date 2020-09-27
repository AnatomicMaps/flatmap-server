import json
import owlready2 as owl


uberon = owl.get_ontology('./uberon.owl').load()
## 'http://purl.obolibrary.org/obo/uberon.owl'

obo = uberon.get_namespace("http://purl.obolibrary.org/obo/")

ANATOMICAL_SYSTEM = 'UBERON_0000467'

summary = {}
anatomical_systems = []
for c in uberon.classes():
    if c.name.startswith('UBERON_'):
        is_a = []
        part_of = []
        for super_class in c.is_a:
            if (isinstance(super_class, owl.entity.ThingClass)
              and super_class.name.startswith('UBERON_')):
                is_a.append(super_class.name)
            elif (isinstance(super_class, owl.class_construct.Restriction)
              and super_class.property == obo.BFO_0000050
              and super_class.value.name.startswith('UBERON_')):
                part_of.append(super_class.value.name)

        if ANATOMICAL_SYSTEM in is_a and len(part_of) == 0:
          anatomical_systems.append(c.name)

        summary[c.name] = { 'is_a': is_a,
                            'label': c.label[0] if c.label else '',
                            'part_of': part_of,
                          }

with open('uberon.json', 'w') as fp:
    json.dump(summary, fp, indent=4)

print('Anatomical Systems:')
for id in anatomical_systems:
  print('  {}  {}'.format(id, summary[id]['label'] if id in summary else ''))
