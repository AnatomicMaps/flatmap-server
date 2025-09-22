#===============================================================================
#
#  Flatmap server tools
#
#  Copyright (c) 2019-2024  David Brooks
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#===============================================================================

from dataclasses import dataclass, field
import logging
import os
from pathlib import Path
import shutil
from typing import Any, cast, Callable, Optional

#===============================================================================

from rich import box, print
from rich.logging import RichHandler
from rich.markdown import Markdown
from rich.prompt import InvalidResponse, PromptBase
from rich.table import Table
from rich.text import Text

#===============================================================================

# Suppress warning on import of ``get_flatmap_list``
os.environ['COMPETENCY_USER'] = 'x'

from mapserver.server.utils import get_flatmap_list
from mapserver.settings import settings

#===============================================================================

FLATMAP_DIRECTORY = 'flatmaps'

STAGING = 'staging'

SERVER_HOME_DIRECTORIES = {
    'curation': '/home/ubuntu/services/curation-flatmap-server',
    'debug': '/home/ubuntu/services/debug-flatmap-server',
    'devel': '/home/ubuntu/services/devel-flatmap-server',
    'fccb': '/home/ubuntu/services/fccb-flatmap-server',
    'isan': '/home/ubuntu/services/isan-flatmap-server',
    'production': '/home/ubuntu/services/prod-flatmap-server',
    STAGING: '/home/ubuntu/services/staging-flatmap-server',
    'local': '.',              ########### Do not commit <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
}

NON_STAGING_SERVERS = list(SERVER_HOME_DIRECTORIES.keys())
NON_STAGING_SERVERS.remove(STAGING)

#===============================================================================

BIOLOGICAL_SEX_IDS = {
    'PATO:0000383': 'female',
    'PATO:0000384': 'male'
}

TAXON_IDENTIFIERS = {
    'NCBITaxon:9685': 'cat',
    'NCBITaxon:9606': 'human',
    'NCBITaxon:10090': 'mouse',
    'NCBITaxon:9823': 'pig',
    'NCBITaxon:10114': 'rat',
}

#===============================================================================

explanation = f"""
Flatmaps are promoted from **staging** to the destination server by copying the
directory containing the flatmap (**flatmap** directories are sub-directories of
a server's `./{FLATMAP_DIRECTORY}` directory.)

Anatomical flatmaps are ordered by their **taxon**, **biological sex** and
**creation time** with only the latest map of a (taxon, biological sex) pair
that is is not already present on the destination, being promoted; functional
maps are ordered by their **creation time**, again with only the latest map
not already present on the destination, being promoted.

A summary of the flatmaps to be promoted is shown before asking the user to
confirm their actual promotion.
"""


def flatmaps_in_directory(directory: Path, map_style: str, taxon: Optional[str]=None, sex: Optional[str]=None) -> list[dict]:
#============================================================================================================================
    settings['FLATMAP_ROOT'] = str(directory)
    flatmaps = get_flatmap_list()
    filtered_maps = []
    for flatmap in flatmaps:
        if flatmap.get('uuid') is None:
            continue
        if flatmap.get('style') != map_style:
            continue
        if flatmap.get('style') == 'anatomical':
            if taxon is not None:
                if flatmap.get('taxon') != taxon:
                    continue
                if sex is not None and flatmap.get('biologicalSex') != sex:
                    continue
            elif flatmap.get('taxon') not in TAXON_IDENTIFIERS:
                continue
        flatmap['relative_path'] = Path(flatmap['path']).relative_to(directory)
        filtered_maps.append(flatmap)
    return filtered_maps

def flatmaps_taxon_reverse_created_order(flatmaps: list[dict]) -> list[dict]:
#============================================================================
    reverse_created_order = sorted(flatmaps, key=lambda flatmap: flatmap.get('created', ''), reverse=True)
    reverse_created_order.sort(key=lambda flatmap: (flatmap.get('taxon', ''), flatmap.get('biologicalSex', '')))
    return reverse_created_order

#===============================================================================
#===============================================================================

@dataclass
class PrintColumn:
    header: str
    fields: str
    params: dict[str, Any] = field(default_factory=dict)
    map: Optional[Callable[[Any], str|Text|None]] = None

FULL_REPORT: list[PrintColumn] = [
    PrintColumn('Nbr', 'map_number'),
    PrintColumn('Name', 'name', {'no_wrap': True}),
    PrintColumn('Taxon', 'taxon'),
    PrintColumn('Biological Sex', 'biologicalSex'),
    PrintColumn('Created', 'created'),
    PrintColumn('UUID', 'relative_path'),
]

#===============================================================================

class FlatmapReporter:
    def __init__(self, functional=False):
        self.__columns = FULL_REPORT
        if functional:
            del self.__columns[2:4]   # Remove Taxon and Biological Sex

    def __get_print_row(self, flatmap: dict) -> list[str|Text]:
    #==========================================================
        row: list[str|Text] = []
        for column in self.__columns:
            fields = column.fields.split('.')
            value = flatmap
            for field in fields:
                value = value.get(field)
                if not isinstance(value, dict):
                    break
            if column.map is not None:
                value = column.map(value)
            if isinstance(value, Text):
                row.append(value)
            else:
                row.append(str(value) if value is not None else '')
        return row

    def print_report(self, flatmaps: list[dict]):
    #============================================
        output = Table(box=box.SIMPLE_HEAD, header_style='bold magenta')
        for column in self.__columns:
            output.add_column(column.header, **column.params)
        for flatmap in flatmaps:
            output.add_row(*self.__get_print_row(flatmap))
        print(output)

#===============================================================================

class Promoter:
    def __init__(self, server: str, map_style='anatomical',
                    taxon: Optional[str]=None, sex: Optional[str]=None):
        self.__map_style = map_style
        self.__taxon = taxon
        self.__sex = sex
        if server not in SERVER_HOME_DIRECTORIES:
            raise ValueError(f'Unknown flatmap server: {server}')
        self.__flatmap_dir = (Path(SERVER_HOME_DIRECTORIES[server]) / FLATMAP_DIRECTORY).resolve()
        self.__staging_dir = (Path(SERVER_HOME_DIRECTORIES[STAGING]) / FLATMAP_DIRECTORY).resolve()
        self.__get_maps_for_promotion()

    @property
    def flatmaps(self) -> list[dict]:
    #================================
        return self.__flatmaps

    def promote_maps(self, numbers: Optional[list[int]]):
    #====================================================
        for flatmap in self.__flatmaps:
            if numbers is None or flatmap['map_number'] in numbers:
                self.__promote_map(flatmap)

    def __promote_map(self, flatmap: dict):
    #======================================
        uuid = flatmap['uuid']
        staging_dir = self.__staging_dir / uuid
        flatmap_dir = self.__flatmap_dir / uuid
        if not flatmap_dir.exists():
            shutil.copytree(staging_dir, flatmap_dir)
            log.info(f"Promoted flatmap {flatmap['map_number']}, {flatmap['name']}: {uuid}")

    def __get_maps_for_promotion(self):
    #==================================
        self.__staging_flatmaps = flatmaps_taxon_reverse_created_order(
                                    flatmaps_in_directory(self.__staging_dir, self.__map_style, self.__taxon, self.__sex))
        self.__flatmaps = []
        last_map_taxon_sex = None
        map_number = 1
        for flatmap in self.__staging_flatmaps:
            map_taxon_sex = (flatmap.get('taxon', ''), flatmap.get('biologicalSex', ''))
            if last_map_taxon_sex != map_taxon_sex:
                last_map_taxon_sex = map_taxon_sex
                if not (self.__flatmap_dir / flatmap['uuid']).exists():
                    flatmap['map_number'] = map_number
                    self.__flatmaps.append(flatmap)
                    map_number += 1

#===============================================================================
#===============================================================================

class MapNumbers(PromptBase[list[str]|list[int]]):
    def process_response(self, value: str) -> list[str]|list[int]:
    #=============================================================
        values = value.strip().lower().replace(',', ' ').split()
        if len(values) == 1 and values[0] in ['a', 'q']:
            return values
        try:
            return [int(n) for n in values]
        except ValueError:
            pass
        if self.choices is not None:
            raise InvalidResponse(f"[prompt.invalid]{self.choices[0]}")
        else:
            raise InvalidResponse(f"[prompt.invalid]Invalid response")

#===============================================================================

def promote(args):
#=================
    promoter = Promoter(args.server, map_style=args.style, taxon=args.taxon, sex=args.biological_sex)
    flatmaps = promoter.flatmaps
    if len(flatmaps) == 0:
        log.info('No flatmaps to promote, exiting.')
        exit(0)

    reporter = FlatmapReporter(args.style=='functional')
    reporter.print_report(flatmaps)

    promote = args.promote
    map_numbers = None
    if not promote:
        valid_numbers = [n + 1 for n in range(len(flatmaps))]
        prompt = ' 1' if len(valid_numbers) == 1 else f's 1..{valid_numbers[-1]}'
        response = MapNumbers.ask(f'Promote flatmap{prompt} to [b]{args.server}[/b]?',
                                    choices=['Q(uit), A(ll) or space separated numbers'],
                                    default='q')
        if len(response) == 1 and response[0] == 'a':
            promote = True
        elif response[0] != 'q':
            promote = True
            map_numbers = sorted(set(cast(list[int], response)))
    if promote:
        promoter.promote_maps(map_numbers)

#===============================================================================

log = logging.getLogger("rich")

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S.%f',
    handlers=[RichHandler(omit_repeated_times = False, show_path=False)]
)

#===============================================================================

def main():
#==========
    import argparse
    from rich_argparse import HelpPreviewAction, RichHelpFormatter

    parser = argparse.ArgumentParser(formatter_class=RichHelpFormatter,
        description='Promote anatomical flatmaps from the Staging flatmap server to a destination server.',
        epilog=Markdown(explanation, style='argparse.text'))            # type: ignore

    parser.add_argument('--generate-help-preview', action=HelpPreviewAction)

    parser.add_argument('server', choices=NON_STAGING_SERVERS,
        help='The destination server to promote flatmaps to.')
    parser.add_argument('--style', choices=['anatomical', 'functional'], default='anatomical',
        help='Style of flatmaps to promote.')
    parser.add_argument('--taxon', choices=list(TAXON_IDENTIFIERS.values()),
        help='Only promote flatmaps for this taxon.')
    parser.add_argument('--biological-sex', choices=list(BIOLOGICAL_SEX_IDS.values()),
        help='Only promote flatmaps of this biological sex.')
    parser.add_argument('--promote', action='store_true', help='Promote flatmaps without confirmation.')

    args = parser.parse_args()

    if args.biological_sex is not None and args.taxon is None:
        exit('--biological-sex can only be used with --taxon')

    promote(args)

#===============================================================================

if __name__ == '__main__':
    main()

#===============================================================================
