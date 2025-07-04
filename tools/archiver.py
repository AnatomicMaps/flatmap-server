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
from pathlib import Path
import shutil
from typing import Any, Callable, Optional

#===============================================================================

from rich import box, print
from rich.logging import RichHandler
from rich.prompt import Confirm
from rich.table import Table
from rich.text import Text

#===============================================================================

from mapserver.server.utils import get_flatmap_list
from mapserver.settings import settings

#===============================================================================

MIN_KEEP_GENERATIONS = 2

#===============================================================================

ARCHIVE_DIRECTORY = 'archive'
FLATMAP_DIRECTORY = 'flatmaps'

PRODUCTION = 'production'

SERVER_HOME_DIRECTORIES = {
    'curation': '/home/ubuntu/services/curation-flatmap-server',
    'debug': '/home/ubuntu/services/debug-flatmap-server',
    'devel': '/home/ubuntu/services/devel-flatmap-server',
    'fccb': '/home/ubuntu/services/fccb-flatmap-server',
    'isan': '/home/ubuntu/services/isan-flatmap-server',
    PRODUCTION: '/home/ubuntu/services/prod-flatmap-server',
    'staging': '/home/ubuntu/services/staging-flatmap-server',
}

#===============================================================================

def flatmaps_in_directory(directory: Path, taxon: Optional[str]=None) -> list[dict]:
#===================================================================================
    settings['FLATMAP_ROOT'] = str(directory)
    flatmaps = get_flatmap_list()
    filtered_maps = []
    for flatmap in flatmaps:
        if flatmap.get('taxon', '') == '':
            flatmap['taxon'] = flatmap['id']
        if taxon is not None and flatmap['taxon'] != taxon:
            continue
        flatmap['relative_path'] = Path(flatmap['path']).relative_to(directory)
        flatmap['size'] = dir_size(flatmap['path'])
        filtered_maps.append(flatmap)
    return filtered_maps

def flatmaps_taxon_reverse_created_order(flatmaps: list[dict]) -> list[dict]:
#============================================================================
    reverse_created_order = sorted(flatmaps, key=lambda flatmap: flatmap.get('created', ''), reverse=True)
    reverse_created_order.sort(key=lambda flatmap: (flatmap.get('taxon', ''), flatmap.get('biologicalSex', '')))
    return reverse_created_order

#===============================================================================
#===============================================================================

def dir_size(path: str|Path) -> int:
#===================================
    return sum([f.lstat().st_size for f in Path(path).glob("**/*")])

def formatted_size(size: int) -> str|Text:
#=========================================
    sz = float(size)
    units = ('B', 'K', 'M', 'G', 'T')
    n = 0
    while n < (len(units)-1):
        if sz < 1024:
            break
        sz /= 1024
        n += 1
    formatted = f'{sz:.0f}{units[n]}'
    if units[n] in ['G', 'T']:
        return Text(formatted, 'bold magenta')
    return formatted

def map_count(n: int) -> str:
#============================
    return '1 map' if n == 1 else f'{n} maps'

#===============================================================================

'''
   'A ' (or ?) to indicate thos that would be archived
'''

@dataclass
class PrintColumn:
    header: str
    fields: str
    params: dict[str, Any] = field(default_factory=dict)
    map: Optional[Callable[[Any], str|Text]] = None

FULL_REPORT: list[PrintColumn] = [
#    PrintColumn('', 'archive', {}, lambda archive: '*' if archive else ''),
    PrintColumn('Taxon', 'taxon'),
    PrintColumn('Biological Sex', 'biologicalSex'),
    PrintColumn('Created', 'created'),
    PrintColumn('Id', 'id', {'no_wrap': True}),
    PrintColumn('Directory', 'relative_path'),
    PrintColumn('Size', 'size', {'justify': 'right'}, formatted_size),
]

SUMMARY_REPORT: list[PrintColumn] = [
    PrintColumn('Taxon', 'taxon'),
    PrintColumn('Biological Sex', 'biologicalSex'),
    PrintColumn('Directory', 'relative_path'),
    PrintColumn('Size', 'size', {'justify': 'right'}, formatted_size),
]

#===============================================================================

class FlatmapReport:
    def __init__(self, full_report=False):
        self.__columns = FULL_REPORT if full_report else SUMMARY_REPORT
        self.__full_report = full_report

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
        total_size = 0
        taxon_maps = 0
        taxon_total = 0
        last_map_taxon_sex = None
        for flatmap in flatmaps:
            if not flatmap.get('archive', False):
                continue
            map_taxon_sex = (flatmap.get('taxon', ''), flatmap.get('biologicalSex', ''))
            if last_map_taxon_sex != map_taxon_sex:
                if last_map_taxon_sex is not None:
                    if self.__full_report:
                        output.add_row(*self.__get_print_row({
                            'relative_path': Text('TOTAL:', 'bold'),
                            'size': taxon_total}), style='bold')
                    else:
                        output.add_row(*self.__get_print_row({
                            'taxon': last_map_taxon_sex[0],
                            'biologicalSex': last_map_taxon_sex[1],
                            'relative_path': f'{map_count(taxon_maps)}, total size:',
                            'size': taxon_total}))
                last_map_taxon_sex = map_taxon_sex
                taxon_maps = 0
                taxon_total = 0
            if self.__full_report:
                output.add_row(*self.__get_print_row(flatmap))
            taxon_maps += 1
            taxon_total += flatmap['size']
            total_size += flatmap['size']
        if last_map_taxon_sex is not None:
            if self.__full_report:
                output.add_row(*self.__get_print_row({
                    'relative_path': Text('TOTAL:', 'bold'),
                    'size': taxon_total}), style='bold')
                output.add_row('')
            else:
                output.add_row(*self.__get_print_row({
                    'taxon': last_map_taxon_sex[0],
                    'biologicalSex': last_map_taxon_sex[1],
                    'relative_path': f'{map_count(taxon_maps)}, total size:',
                    'size': taxon_total}))
        output.add_row(*self.__get_print_row({
            'relative_path': Text('TOTAL SIZE:', 'bold magenta'),
            'size': total_size}))
        print(output)

#===============================================================================

class Archiver:
    def __init__(self, server: str, keep_generations: int=MIN_KEEP_GENERATIONS, taxon: Optional[str]=None):
        if keep_generations < MIN_KEEP_GENERATIONS:
            log.info(f'At least {MIN_KEEP_GENERATIONS} of flatmaps must be kept -- parameter adjusted.')
            keep_generations = MIN_KEEP_GENERATIONS
        self.__keep_generations = keep_generations
        self.__taxon = taxon
        if server not in SERVER_HOME_DIRECTORIES:
            raise ValueError(f'Unknown flatmap server: {server}')
        self.__archive_dir = (Path(SERVER_HOME_DIRECTORIES[server]) / ARCHIVE_DIRECTORY).resolve()
        if not self.__archive_dir.exists():
            self.__archive_dir.mkdir()
        elif not self.__archive_dir.is_dir():
            raise ValueError(f'Cannot create archive directory: {str(self.__archive_dir)}')
        self.__flatmap_dir = (Path(SERVER_HOME_DIRECTORIES[server]) / FLATMAP_DIRECTORY).resolve()
        self.__refresh_map_list()

    @property
    def flatmaps(self) -> list[dict]:
    #================================
        return self.__flatmaps

    def archive_maps(self):
    #======================
        for flatmap in self.__flatmaps:
            if flatmap.get('archive', False):
                self.__archive_map(flatmap['relative_path'])
        self.__refresh_map_list()

    def __archive_map(self, flatmap_path: str):
    #==========================================
        flatmap_dir = self.__flatmap_dir / flatmap_path
        if flatmap_dir.exists() and flatmap_dir.is_dir():
            archive_dir = self.__archive_dir / flatmap_path
            if archive_dir.exists():
                if archive_dir.is_file() or archive_dir.is_symlink():
                    archive_dir.unlink()
                elif archive_dir.is_dir():
                    shutil.rmtree(archive_dir)
                else:
                    log.error(f'Cannot remove existing flatmap archive ({archive_dir}) -- map not archived')
                    return
            flatmap_dir.rename(archive_dir)
            log.info(f'Archived flatmap {flatmap_path}...')

    def __refresh_map_list(self):
    #============================
        self.__flatmaps = flatmaps_taxon_reverse_created_order(
                                flatmaps_in_directory(self.__flatmap_dir, self.__taxon))
        generation_count = 0
        last_map_taxon_sex = None
        for flatmap in self.__flatmaps:
            map_taxon_sex = (flatmap.get('taxon', ''), flatmap.get('biologicalSex', ''))
            if last_map_taxon_sex != map_taxon_sex:
                last_map_taxon_sex = map_taxon_sex
                generation_count = 0
            generation_count += 1
            if generation_count > self.__keep_generations:
                flatmap['archive'] = True

#===============================================================================
#===============================================================================

def archive(args):
#=================
    archiver = Archiver(args.server, keep_generations=args.keep, taxon=args.taxon)
    flatmaps = archiver.flatmaps

    report = FlatmapReport(full_report=args.full)
    report.print_report(flatmaps)
    if args.report:
        return

    archivable = len([f for f in flatmaps if f.get('archive', False)])
    if not archivable:
        log.info('No flatmaps to archive, exiting.')
        exit(0)

    archive = args.archive
    if not archive:
        archive = Confirm.ask(f"Archive the above flatmaps, keeping {args.keep} versions?", default=False)
    if archive:
        archiver.archive_maps()

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

    parser = argparse.ArgumentParser(description='Report on and archive maps on a flatmap server.')

    parser.add_argument('server', choices=list(SERVER_HOME_DIRECTORIES.keys()),
        help='The server containing flatmaps to be archived')
    parser.add_argument('--keep', type=int, default=MIN_KEEP_GENERATIONS+1,
        help='The number of recent versions of a flatmap to retain')
    parser.add_argument('--full', action='store_true', help='Show details of flatmaps that would be archived')
    parser.add_argument('--report', action='store_true', help="Only report details and don't archive flatmaps")
    parser.add_argument('--taxon', help="Only report details flatmaps with this taxon identifier")
    parser.add_argument('--archive', action='store_true', help='Archive flatmaps without confirmation')

    args = parser.parse_args()
    if args.keep < MIN_KEEP_GENERATIONS:
        exit(f'--keep must be at least {MIN_KEEP_GENERATIONS}')

    archive(args)

#===============================================================================

if __name__ == '__main__':
    main()

#===============================================================================
