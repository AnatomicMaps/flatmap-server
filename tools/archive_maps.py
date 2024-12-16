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

import json
from pathlib import Path
import shutil

#===============================================================================

ARCHIVE_DIRECTORY = 'archive'
FLATMAP_DIRECTORY = 'flatmaps'

SERVER_HOME_DIRECTORIES = {
    'curation': '/home/ubuntu/services/curation-flatmap-server',
    'debug': '/home/ubuntu/services/debug-flatmap-server',
    'devel': '/home/ubuntu/services/devel-flatmap-server',
    'fccb': '/home/ubuntu/services/fccb-flatmap-server',
    'isan': '/home/ubuntu/services/isan-flatmap-server',
    'production': '/home/ubuntu/services/prod-flatmap-server',
    'staging': '/home/ubuntu/services/staging-flatmap-server',
}

#===============================================================================

class Archiver:
    def __init__(self, server: str, execute: bool=False):
        if server not in SERVER_HOME_DIRECTORIES:
            raise ValueError(f'Unknown flatmap server: {server}')
        self.__archive_dir = Path(SERVER_HOME_DIRECTORIES[server]) / ARCHIVE_DIRECTORY
        if not self.__archive_dir.exists():
            print(f'mkdir {str(self.__archive_dir)}')
            if execute:
                self.__archive_dir.mkdir()
        elif not self.__archive_dir.is_dir():
            raise ValueError(f'Cannot create archive: {str(self.__archive_dir)}')
        self.__flatmap_dir = Path(SERVER_HOME_DIRECTORIES[server]) / FLATMAP_DIRECTORY
        self.__execute = execute

    def archive(self, flatmap_uuid: str):
        flatmap_dir = self.__flatmap_dir / flatmap_uuid
        if flatmap_dir.exists() and flatmap_dir.is_dir():
            archive_dir = self.__archive_dir / flatmap_uuid
            if archive_dir.exists():
                if archive_dir.is_file() or archive_dir.is_symlink():
                    print(f'rm {str(archive_dir)}')
                    if self.__execute:
                        archive_dir.unlink()
                elif archive_dir.is_dir():
                    print(f'rm -rf {str(archive_dir)}')
                    if self.__execute:
                        shutil.rmtree(archive_dir)
                else:
                    raise ValueError(f'Cannot remove existing flatmap archive: {str(archive_dir)}')
            print(f'mv {str(flatmap_dir)} {str(self.__archive_dir)}')
            if self.__execute:
                flatmap_dir.rename(archive_dir)

#===============================================================================

def process_export(server: str, export_file: str, execute: bool=False):
    archiver = Archiver(server, execute=execute)
    with open(export_file) as fp:
        records = json.load(fp)
    for flatmap in records:
        if server in flatmap['servers']:
            archiver.archive(flatmap['uuid'])

#===============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Create a script to archive flatmaps from a dashboard export')
    parser.add_argument('server', metavar='SERVER', help='The server containing flatmaps to be archived',
        choices=list(SERVER_HOME_DIRECTORIES.keys()))
    parser.add_argument('flatmap_export', metavar='FLATMAP_EXPORT', help='A flatmap dashboard export file')
    args = parser.parse_args()

    process_export(args.server, args.flatmap_export, execute=False)

#===============================================================================

if __name__ == '__main__':
    main()

#===============================================================================
