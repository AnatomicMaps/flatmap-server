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

import cytoscape from 'cytoscape'

//==============================================================================

export type KnowledgeNode = [string, string[]]

type KnowledgeEdge = [KnowledgeNode, KnowledgeNode]

export interface ConnectivityKnowledge
{
    connectivity: KnowledgeEdge[]
    axons: KnowledgeNode[]
    dendrites: KnowledgeNode[]
}

//==============================================================================

type GraphNode = {
    id: string
    label: string
    axon?: boolean
    dendrite?: boolean
}

type GraphEdge = {
    id: string
    source: string
    target: string
}

//==============================================================================

export class ConnectivityGraph
{
    #cy: CytoscapeGraph|null = null
    #nodes: GraphNode[] = []
    #edges: GraphEdge[] = []
    #axons: string[]
    #dendrites: string[]
    #labelCache: Map<string, string>

    constructor(labelCache: Map<string, string>)
    {
        this.#labelCache = labelCache
    }

    async addConnectivity(knowledge: ConnectivityKnowledge)
    //=====================================================
    {
        this.#axons = knowledge.axons.map(node => JSON.stringify(node))
        this.#dendrites = knowledge.dendrites.map(node => JSON.stringify(node))
        if (knowledge.connectivity.length) {
            for (const edge of knowledge.connectivity) {
                const e0 = await this.#graphNode(edge[0])
                const e1 = await this.#graphNode(edge[1])
                this.#nodes.push(e0)
                this.#nodes.push(e1)
                this.#edges.push({
                    id: `${e0.id}_${e1.id}`,
                    source: e0.id,
                    target: e1.id
                })
            }
        } else {
            this.#nodes.push({
                id: 'MISSING',
                label: 'NO PATHS'
            })
        }
    }

    showConnectivity()
    //================
    {
        this.#cy = new CytoscapeGraph(this)
    }

    clearConnectivity()
    //=================
    {
        if (this.#cy) {
            this.#cy.remove()
            this.#cy = null
        }
    }

    get elements()
    //============
    {
        return [
            ...this.#nodes.map(n => { return {data: n}}),
            ...this.#edges.map(e => { return {data: e}})
        ]
    }

    get roots(): string[]
    //===================
    {
        return this.#dendrites
    }

    async #graphNode(node: KnowledgeNode): Promise<GraphNode>
    //=======================================================
    {
        const id = JSON.stringify(node)
        const label = [node[0], ...node[1]]
        const humanLabels: string[] = []
        for (const term of label) {
            const humanLabel = this.#labelCache.has(term) ? this.#labelCache.get(term) : ''
            humanLabels.push(humanLabel)
        }
        label.push(...humanLabels)

        const result = {
            id,
            label: label.join('\n')
        }
        if (this.#axons.includes(id)) {
            if (this.#dendrites.includes(id)) {
                result['both-a-d'] = true
            } else {
                result['axon'] = true
            }
        } else if (this.#dendrites.includes(id)) {
            result['dendrite'] = true

        }
        return result
    }
}

//==============================================================================

const GRAPH_STYLE = [
    {
        'selector': 'node',
        'style': {
            'label': 'data(label)',
            'background-color': '#80F0F0',
            'text-valign': 'center',
            'text-wrap': 'wrap',
            'text-max-width': '80px',
            'font-size': '6px'
        }
    },
    {
        'selector': 'node[axon]',
        'style': {
            'background-color': 'green'
        }
    },
    {
        'selector': 'node[dendrite]',
        'style': {
            'background-color': 'red'
        }
    },
    {
        'selector': 'node[both-a-d]',
        'style': {
            'background-color': 'gray'
        }
    },
    {
        'selector': 'edge',
        'style': {
            'width': 2,
            'line-color': '#9dbaea',
            'target-arrow-color': '#9dbaea',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier'
        }
    }
]

//==============================================================================

class CytoscapeGraph
{
    #cy
    #tooltip: HTMLElement

    constructor(connectivityGraph: ConnectivityGraph)
    {
        const graphCanvas = document.getElementById('graph-canvas')

        this.#cy = cytoscape({
            container: graphCanvas,
            elements: connectivityGraph.elements,
            layout: {
                name: 'breadthfirst',
                circle: false,
                roots: connectivityGraph.roots
            },
            directed: true,
            style: GRAPH_STYLE
        }).on('mouseover', 'node', this.#overNode.bind(this))
          .on('mouseout', 'node', this.#exitNode.bind(this))
          .on('position', 'node', this.#moveNode.bind(this))

        this.#tooltip = document.createElement('div')
        this.#tooltip.id = 'tooltip'
        this.#tooltip.hidden = true
        graphCanvas!.lastChild!.appendChild(this.#tooltip)
    }

    remove()
    //======
    {
        if (this.#cy) {
            this.#cy.destroy()
        }
    }

    #checkRightBoundary(leftPos: number)
    //==================================
    {
        if ((leftPos + this.#tooltip.offsetWidth) >= this.#tooltip.parentElement!.offsetWidth) {
            this.#tooltip.style.left = `${leftPos - this.#tooltip.offsetWidth}px`
        }
    }

    #overNode(event)
    //==============
    {
        const node = event.target
        this.#tooltip.innerText = node.data().label
        this.#tooltip.style.left = `${event.renderedPosition.x}px`
        this.#tooltip.style.top = `${event.renderedPosition.y}px`
        this.#tooltip.hidden = false
        this.#checkRightBoundary(event.renderedPosition.x)
    }

    #moveNode(event)
    //==============
    {
        const node = event.target
        this.#tooltip.style.left = `${node.renderedPosition().x}px`
        this.#tooltip.style.top = `${node.renderedPosition().y}px`
        this.#checkRightBoundary(node.renderedPosition().x)
    }

    #exitNode(event)
    //==============
    {
        this.#tooltip.hidden = true
    }
}

//==============================================================================
