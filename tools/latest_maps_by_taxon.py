#===============================================================================
#
#  Flatmap tools
#
#  Copyright (c) 2023 David Brooks
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

import argparse
import json
import logging
import os
import pathlib
import sqlite3

#===============================================================================

from landez.sources import MBTilesReader, ExtractionError, InvalidFormatError

#===============================================================================

def read_metadata(tile_reader, name):
    try:
        row = tile_reader._query("SELECT value FROM metadata WHERE name='{}'".format(name)).fetchone()
        return {} if row is None else json.loads(row[0])
    except (InvalidFormatError, sqlite3.OperationalError):
        raise IOError('Cannot read tile database')

#===============================================================================

def main():

    parser = argparse.ArgumentParser(description='Print latest maps on a map server')
    parser.add_argument('--all-maps', action='store_true', help='Print all maps')
    parser.add_argument('--tar-script', metavar='TAR_SCRIPT', help='Script to create to archive flatmap directories', default='tar_latest.sh')
    parser.add_argument('--archive-name', metavar='ARCHIVE_NAME', help='Name of archive to create', default='./latest_flatmaps.tar.gz')
    parser.add_argument('--flatmaps', dest='flatmap_root', metavar='FLATMAP_ROOT', default='./flatmaps')
    args = parser.parse_args()

    flatmaps_by_dir = {}
    root_path = pathlib.Path(args.flatmap_root).absolute()
    if root_path.is_dir():
        for flatmap_dir in root_path.iterdir():
            index = os.path.join(args.flatmap_root, flatmap_dir, 'index.json')
            mbtiles = os.path.join(args.flatmap_root, flatmap_dir, 'index.mbtiles')
            if os.path.isdir(flatmap_dir) and os.path.exists(index) and os.path.exists(mbtiles):
                with open(index) as fp:
                    index = json.loads(fp.read())
                version = index.get('version', 1.0)
                reader = MBTilesReader(mbtiles)
                if version >= 1.3:
                    metadata = read_metadata(reader, 'metadata')
                    if (('id' not in metadata or flatmap_dir.name != metadata['id'])
                     and ('uuid' not in metadata or flatmap_dir.name != metadata['uuid'].split(':')[-1])):
                        logging.error(f'Flatmap id mismatch: {flatmap_dir}')
                        continue
                    flatmap = {
                        'id': metadata['id'],
                        'source': metadata['source'],
                        'version': version
                    }
                    if 'created' in metadata:
                        flatmap['created'] = metadata['created']
                    if 'taxon' in metadata:
                        flatmap['taxon'] = metadata['taxon']
                        flatmap['describes'] = metadata['describes'] if 'describes' in metadata else flatmap['taxon']
                    elif 'describes' in metadata:
                        flatmap['taxon'] = metadata['describes']
                        flatmap['describes'] = flatmap['taxon']
                    if 'biological-sex' in metadata:
                        flatmap['biologicalSex'] = metadata['biological-sex']
                    if 'uuid' in metadata:
                        flatmap['uuid'] = metadata['uuid']
                    if 'name' in metadata:
                        flatmap['name'] = metadata['name']
                else:
                    try:
                        source_row = reader._query("SELECT value FROM metadata WHERE name='source'").fetchone()
                    except (InvalidFormatError, sqlite3.OperationalError):
                        raise IOError(f'Cannot read tile database: {mbtiles}')
                    if source_row is None:
                        continue
                    flatmap = {
                        'id': flatmap_dir.name,
                        'source': source_row[0]
                    }
                    created = reader._query("SELECT value FROM metadata WHERE name='created'").fetchone()
                    if created is not None:
                        flatmap['created'] = created[0]
                    describes = reader._query("SELECT value FROM metadata WHERE name='describes'").fetchone()
                    if describes is not None and describes[0]:
                        flatmap['describes'] = describes[0]
                flatmaps_by_dir[str(flatmap_dir)] = flatmap

    if not args.all_maps:
        maps_by_taxon_sex = {}
        for flatmap_dir, flatmap in flatmaps_by_dir.items():
            if ((created := flatmap.get('created')) is not None
            and (taxon := flatmap.get('taxon', flatmap.get('describes'))) is not None):
                map_key = (taxon, flatmap.get('biologicalSex', ''))
                if (map_key not in maps_by_taxon_sex
                 or created > maps_by_taxon_sex[map_key][0]):
                    maps_by_taxon_sex[map_key] = (created, flatmap_dir, flatmap)
        flatmaps_by_dir = { flatmap_dir: flatmap for _, flatmap_dir, flatmap in maps_by_taxon_sex.values() }

    print(json.dumps(flatmaps_by_dir, indent=4))

    if args.tar_script:
        root_path_len = len(str(root_path)) + 1
        with open(args.tar_script, 'w') as fp:
            fp.write('#!/bin/sh\n\n')
            fp.write('  \\\n    '.join([f'tar czvf {args.archive_name} -C {root_path}']
                                     + [flatmap_dir[root_path_len:] for flatmap_dir in flatmaps_by_dir.keys()]))
            fp.write('\n')

#===============================================================================

if __name__ == '__main__':
#=========================
    main()

#===============================================================================
