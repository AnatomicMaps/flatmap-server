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

import { ConnectivityGraph, ConnectivityKnowledge, KnowledgeNode } from './graph'

//==============================================================================

export class App
{
    #connectivityGraph: ConnectivityGraph|null
    #knowledgeByPath: Map<string, ConnectivityKnowledge> = new Map()
    #labelCache: Map<string, string> = new Map()
    #labelledTerms: Set<string> = new Set()
    #mapServer: string
    #pathPrompt: HTMLElement
    #pathSelector: HTMLElement
    #sourceSelector: HTMLElement
    #spinner: HTMLElement

    constructor(mapServer: string)
    {
        this.#mapServer = mapServer
        this.#sourceSelector = document.getElementById('source-selector')
        this.#pathPrompt = document.getElementById('path-prompt')
        this.#pathSelector = document.getElementById('path-selector')
        this.#spinner = document.getElementById('spinner')
    }

    async run()
    //=========
    {
        this.#showSpinner()
        const selectedSource = await this.#setSourceList()
        this.#sourceSelector.onchange = async (e) => {
            // @ts-ignore
            if (e.target.value !== '') {
                // @ts-ignore
                await this.#setPathList(e.target.value)
                this.#clearConnectivity()
            }
        }
        await this.#setPathList(selectedSource)
        this.#pathSelector.onchange = async (e) => {
            // @ts-ignore
            if (e.target.value !== '') {
                // @ts-ignore
                await this.#showGraph(e.target.value)
            } else {
                this.#clearConnectivity()
            }
        }
        this.#hideSpinner()
        this.#showPrompt()
    }

    async #showGraph(neuronPath: string)
    //==================================
    {
        this.#hidePrompt()
        this.#showSpinner()
        this.#connectivityGraph = new ConnectivityGraph(this.#labelCache)
        await this.#connectivityGraph.addConnectivity(this.#knowledgeByPath.get(neuronPath))
        this.#hideSpinner()
        this.#connectivityGraph.showConnectivity()
    }

    #clearConnectivity()
    //==================
    {
        if (this.#connectivityGraph) {
            this.#connectivityGraph.clearConnectivity()
            this.#connectivityGraph = null
            this.#showPrompt()
        }
    }

    #hidePrompt()
    //===========
    {
        this.#pathPrompt.style.display = 'none'
    }
    #showPrompt()
    //===========
    {
        this.#pathPrompt.style.display = 'block'
    }

    #hideSpinner()
    //============
    {
        this.#spinner.style.display = 'none'
    }
    #showSpinner()
    //============
    {
        this.#spinner.style.display = 'block'
    }

    async #query(sql: string, params: string[]=[])
    //============================================
    {
        const url = `${this.#mapServer}knowledge/query/`
        const query = { sql, params }
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
        return await response.json()
    }

    async #getCachedTermLabels()
    //==========================
    {
        if (this.#labelledTerms.size) {
            const termLabels = await this.#query(`
                select entity, label from labels
                    where entity in (?${', ?'.repeat(this.#labelledTerms.size-1)})`,
                [...this.#labelledTerms.values()])
            for (const termLabel of termLabels.values) {
                this.#labelCache.set(termLabel[0], termLabel[1])
            }
        }
    }

    #cacheNodeLabels(node: KnowledgeNode)
    //===================================
    {
        for (const term of [node[0], ...node[1]]) {
            this.#labelledTerms.add(term)
        }
    }

    async #cacheLabels(knowledge: ConnectivityKnowledge)
    //==================================================
    {
        for (const edge of knowledge.connectivity) {
            this.#cacheNodeLabels(edge[0])
            this.#cacheNodeLabels(edge[1])
        }
    }

    async #setPathList(source: string): Promise<string>
    //=================================================
    {
        const data = await this.#query(
            `select entity, knowledge from knowledge
                where entity like 'ilxtr:%' and source=?
                order by entity`,
            [source])
        const pathList: string[] = ['<option value="">Please select path:</option>']
        this.#knowledgeByPath.clear()
        this.#labelledTerms = new Set()
        for (const [key, jsonKnowledge] of data.values) {
            const knowledge = JSON.parse(jsonKnowledge)
            if ('connectivity' in knowledge) {
                const label = knowledge.label || key
                const shortLabel = (label === key.slice(6).replace('-prime', "'").replaceAll('-', ' ')) ? ''
                                 : (label.length < 50) ? label : `${label.slice(0, 50)}...`
                pathList.push(`<option value="${key}" label="${key}&nbsp;&nbsp;${shortLabel}"></option>`)
                this.#knowledgeByPath.set(key, knowledge)
                this.#cacheLabels(knowledge)
            }
        }
        await this.#getCachedTermLabels()
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
