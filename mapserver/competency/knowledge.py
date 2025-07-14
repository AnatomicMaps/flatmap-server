#===============================================================================
#
#  Flatmap server
#
#  Copyright (c) 2019-25  David Brooks
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

from collections import defaultdict

#===============================================================================

from mapknowledge.competency import CompetencyDatabase

#===============================================================================

class CompetencyKnowledge(CompetencyDatabase):

    def term_descriptions(self, source: str) -> dict[str, str]:
    #==========================================================
        return { row[0]: row[1]
            for row in self.execute(
                'select term_id, description from feature_terms where source_id=%s', (source,)) }

    def path_properties(self, source: str) -> dict:
    #==============================================
        path_properties = {}
        for row in self.execute(
                'select path_id, alert, biological_sex, disconnected from path_properties where source_id=%s', (source,)):
            properties = {}
            if row[1] is not None:
                properties['alert'] = row[1]
            if row[2] is not None:
                properties['biologicalSex'] = row[2]
            if row[3] is not None:
                properties['pathDisconnected'] = row[3]
            path_properties[row[0]] = properties
        return path_properties

    def path_evidence(self, source: str) -> dict[str, list[str]]:
    #============================================================
        path_evidence = defaultdict(list)
        for row in self.execute(
                'select term_id, evidence_id from feature_evidence where source_id=%s', (source,)):
            path_evidence[row[0]].append(row[1])
        return path_evidence

    def path_phenotypes(self, source: str) -> dict[str, list[str]]:
    #==============================================================
        path_phenotypes = defaultdict(list)
        for row in self.execute(
                'select path_id, phenotype from path_phenotypes where source_id=%s', (source,)):
            path_phenotypes[row[0]].append(row[1])
        return path_phenotypes

#===============================================================================
#===============================================================================
