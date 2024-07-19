#===============================================================================

from typing import Optional

#===============================================================================

ILX_BASE = 'http://uri.interlex.org/base/ilx_'
ILX_PREFIX = 'ILX:'

UBERON_BASE = 'http://purl.obolibrary.org/obo/UBERON_'
UBERON_PREFIX = 'UBERON:'

NAMESPACES = [
    (ILX_PREFIX,    ILX_BASE),
    (UBERON_PREFIX, UBERON_BASE),
    ('BFO:',        'http://purl.obolibrary.org/obo/BFO_'),
]

#===============================================================================

class Uri:
    def __init__(self, uri: str):
        self.__uri = str(uri)
        if uri.startswith('http:') or uri.startswith('https:'):
            for namespace in NAMESPACES:
                if uri.startswith(namespace[1]):
                    colon = '' if namespace[0].endswith(':') else ':'
                    self.__uri = f'{namespace[0]}{colon}{uri[len(namespace[1]):]}'
                    break

    def __eq__(self, other) -> bool:
        return hash(self.__uri) == hash(other)

    def __hash__(self)-> int:
        return hash(self.__uri)

    def __str__(self) -> str:
        return self.__uri

    @property
    def id(self) -> str:
        return self.__uri

    @property
    def is_ilx(self) -> bool:
        return self.__uri.startswith(ILX_PREFIX)

    @property
    def is_uberon(self) -> bool:
        return self.__uri.startswith(UBERON_PREFIX)

    @property
    def sparc_term(self) -> bool:
        return self.is_uberon or self.is_ilx

#===============================================================================

class Node(Uri):
    def __init__(self, node: dict):
        super().__init__(node['id'])
        self.__label = node.get('lbl', str(super()))

    @classmethod
    def from_uri(cls, uri):
        return cls({'id': str(uri)})

    def __str__(self) -> str:
        return self.__label

#===============================================================================

class Triple:
    def __init__(self, edge: dict):
        self.__subject = Uri(edge['sub'])
        self.__predicate = Uri(edge['pred'])
        self.__object = Uri(edge['obj'])
        self.__metadata = edge.get('meta', None)

    def __str__(self) -> str:
        return f'<{self.s}, {self.p}, {self.o}>'

    @property
    def s(self) -> Uri:
        return self.__subject

    @property
    def p(self) -> Uri:
        return self.__predicate

    @property
    def o(self) -> Uri:
        return self.__object

    @property
    def metadata(self) -> Optional[dict]:
        return self.__metadata

#===============================================================================
