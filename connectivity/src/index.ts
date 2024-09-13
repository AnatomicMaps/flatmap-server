/*==============================================================================

A viewer for neuron connectivity graphs.

Copyright (c) 2019 - 2024  David Brooks

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

==============================================================================*/

import { ConnectivityGraph, CytoscapeGraph } from './graph'

//==============================================================================

/*

        mapSelector.innerHTML = mapList.join('')
        mapSelector.onchange = (e) => {
            if (e.target.value !== '') {
                setGenerationSelector(e.target.value)
                loadMap(currentManager, e.target.value)
            }
        }
        mapGeneration.onchange = (e) => {
            if (e.target.value !== '') {
                loadMap(currentManager, e.target.value)
            }
        }


        const generationList = []
        const mapName = mapIdToName.get(mapId)
        if (mapName) {
            for (const map of mapGenerations.get(mapName)) {
                const id = ('uuid' in map) ? map.uuid : map.id
                const selected = (mapId === id) ? 'selected' : ''
                generationList.push(`<option value="${id}" ${selected}>${map.created}</option>`)
            }
        }
        mapGeneration.innerHTML = generationList.join('')




 */

//==============================================================================

export class App
{
    #connectivityGraph: ConnectivityGraph|null
    #mapServer: string
    #pathSelector: HTMLElement
    #sourceSelector: HTMLElement

    constructor(mapServer: string)
    {
        this.#mapServer = mapServer
        this.#sourceSelector = document.getElementById('source-selector')
        this.#pathSelector = document.getElementById('path-selector')
    }

    async run()
    //=========
    {
        const selectedSource = await this.#setSourceList()
        this.#sourceSelector.onchange = async (e) => {
            // @ts-ignore
            if (e.target.value !== '') {
                // @ts-ignore
                await this.#setPathList(e.target.value)
            }
        }

        await this.#setPathList(selectedSource)
        this.#pathSelector.onchange = async (e) => {
            // @ts-ignore
            if (e.target.value !== '') {
                // @ts-ignore
                await this.#showGraph(e.target.value)
            } else if (this.#connectivityGraph) {
                this.#connectivityGraph.clearConnectivity()
                this.#connectivityGraph = null
            }
        }
    }

    async #showGraph(neuronPath: string)
    //==================================
    {
        this.#connectivityGraph = new ConnectivityGraph(this.#mapServer)
        await this.#connectivityGraph.addConnectivity(neuronPath)
        this.#connectivityGraph.showConnectivity()
    }

    async #setPathList(source: string): Promise<string>
    //=================================================
    {
        const url = `${this.#mapServer}/knowledge/query/`
        const query = {
            sql: `select distinct k.entity, l.label from knowledge as k
                    left join labels as l on k.entity=l.entity
                    where k.entity like 'ilxtr:%' and source=?
                    order by k.entity`,
            params: [source]
        }
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                "Accept": "application/json; charset=utf-8",
                "Cache-Control": "no-store",
                "Content-Type": "application/json"
            },
            body: JSON.stringify(query)
        })
        if (!response.ok) {
            throw new Error(`Cannot access ${url}`)
        }
        const data = await response.json()
        const pathList: string[] = ['<option value="">Please select path:</option>']
        for (const [key, label] of data.values) {
            pathList.push(`<option value="${key}" label="${key}&nbsp;&nbsp;${label.slice(0, 50)}..."></option>`)
        }
        this.#pathSelector.innerHTML = pathList.join('')
        return ''
    }

    async #setSourceList(): Promise<string>
    //=====================================
    {
        const url = `${this.#mapServer}/knowledge/sources`
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                "Accept": "application/json; charset=utf-8",
                "Cache-Control": "no-store",
                "Content-Type": "application/json"
            }
        })
        if (!response.ok) {
            throw new Error(`Cannot access ${url}`)
        }
        const data = await response.json()
        const sources = data.sources

        // Order with most recent first...
        let firstSource = ''
        const sourceList: string[] = []
        for (const source of sources) {
            if (source) {
                sourceList.push(`<option value="${source}">${source}</option>`)
                if (firstSource === '') {
                    firstSource = source
                }
            }
        }
        this.#sourceSelector.innerHTML = sourceList.join('')
        return firstSource
    }
}

//==============================================================================
