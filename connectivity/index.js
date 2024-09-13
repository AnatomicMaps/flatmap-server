import { ConnectivityGraph, CytoscapeGraph } from './src'

//==============================================================================

const MAP_SERVER = 'https://mapcore-demo.org/curation/flatmap/'

//http://localhost:8000/

const neuron_path = 'ilxtr:neuron-type-aacar-5'

//==============================================================================

//const knowledge = await loadKnowledge('ilxtr:neuron-type-splen-3')
//const knowledge = await loadKnowledge('ilxtr:neuron-type-bolew-unbranched-3')
//const knowledge = await loadKnowledge('ilxtr:neuron-type-keast-9')

const connectivityGraph = new ConnectivityGraph(MAP_SERVER)
await connectivityGraph.addConnectivity(neuron_path)

const cy = new CytoscapeGraph(connectivityGraph)

