#===============================================================================
#
#  Flatmap viewer and annotation tools
#
#  Copyright (c) 2019  David Brooks
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

import os

#===============================================================================

from hypercorn.config import Config

#===============================================================================

# Global server settings

config = Config()

#===============================================================================

# Needed to read JPEG 2000 files with OpenCV2 under Linux

os.environ['OPENCV_IO_ENABLE_JASPER'] = '1'

#===============================================================================
#===============================================================================

# Global settings

settings = {}

settings['ROOT_PATH'] = os.path.split(os.path.dirname(os.path.abspath(__file__)))[0]

def normalise_path(path):
#========================
    return os.path.normpath(os.path.join(settings['ROOT_PATH'], path))

#===============================================================================

FLATMAP_ROOT = os.environ.get('FLATMAP_ROOT', './flatmaps')
settings['FLATMAP_ROOT'] = normalise_path(FLATMAP_ROOT)
if not os.path.exists(settings['FLATMAP_ROOT']):
    exit(f'Missing {settings["FLATMAP_ROOT"]} directory -- set FLATMAP_ROOT environment variable to the full path and/or create directory')

FLATMAP_VIEWER = os.environ.get('FLATMAP_VIEWER', './viewer')
settings['FLATMAP_VIEWER'] = normalise_path(FLATMAP_VIEWER)

FLATMAP_SERVER_LOGS = os.environ.get('FLATMAP_SERVER_LOGS', './logs')
settings['FLATMAP_SERVER_LOGS'] = normalise_path(FLATMAP_SERVER_LOGS)
if not os.path.exists(settings['FLATMAP_SERVER_LOGS']):
    exit(f'Missing {settings["FLATMAP_SERVER_LOGS"]} directory -- set FLATMAP_SERVER_LOGS environment variable to the full path and/or create directory')

MAPMAKER_LOGS = os.environ.get('MAPMAKER_LOGS', os.path.join(FLATMAP_SERVER_LOGS, 'mapmaker'))
settings['MAPMAKER_LOGS'] = normalise_path(MAPMAKER_LOGS)

#===============================================================================

# Bearer tokens for service authentication

settings['ANNOTATOR_TOKENS'] = os.environ.get('ANNOTATOR_TOKENS', '').split()
settings['MAPMAKER_TOKENS'] = os.environ.get('MAPMAKER_TOKENS', '').split()

#===============================================================================
#===============================================================================
