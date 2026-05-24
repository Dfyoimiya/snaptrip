import { useMemo } from "react"
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  MarkerType,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import { useAgentStore } from "../../stores/agentStore"
import { PipelineNode } from "./PipelineNode"
import type { PipelineNodeData } from "../../types/agent"

const nodeTypes = { pipelineNode: PipelineNode }

function buildGraph(
  nodes: { id: string; label: string; status: string; layer: number }[],
): { rfNodes: Node<PipelineNodeData>[]; rfEdges: Edge[] } {
  const layers: Record<number, string[]> = {}
  for (const n of nodes) {
    (layers[n.layer] ??= []).push(n.id)
  }

  const rfNodes: Node<PipelineNodeData>[] = nodes.map((n) => ({
    id: n.id,
    type: "pipelineNode",
    position: { x: 0, y: 0 }, // layout applied below
    data: {
      label: n.label,
      status: n.status as PipelineNodeData["status"],
      layer: n.layer,
      type: n.id.includes("monitor") ? "monitor" :
            n.id.includes("consensus") ? "checkpoint" : "engine",
    },
  }))

  // Layout: horizontal left→right, vertical center within layer
  const LAYER_X_GAP = 220
  const NODE_Y_GAP = 80
  const sortedLayers = Object.keys(layers).map(Number).sort((a, b) => a - b)

  for (const layerNum of sortedLayers) {
    const ids = layers[layerNum]
    const totalHeight = (ids.length - 1) * NODE_Y_GAP
    const startY = -totalHeight / 2
    ids.forEach((id, i) => {
      const n = rfNodes.find((n) => n.id === id)!
      n.position = { x: layerNum * LAYER_X_GAP, y: startY + i * NODE_Y_GAP }
    })
  }

  // Edges: connect across layers (sequential within same layer, fan to all next-layer)
  const rfEdges: Edge[] = []
  for (let i = 0; i < sortedLayers.length - 1; i++) {
    const fromLayer = sortedLayers[i]
    const toLayer = sortedLayers[i + 1]
    const fromIds = layers[fromLayer]
    const toIds = layers[toLayer]

    if (fromIds.length === 1 && toIds.length === 1) {
      rfEdges.push({
        id: `${fromIds[0]}→${toIds[0]}`,
        source: fromIds[0],
        target: toIds[0],
        type: "smoothstep",
        animated: true,
        style: { stroke: "#52525b", strokeWidth: 1.5 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#52525b", width: 12, height: 12 },
      })
    } else {
      // Fan: each from connects to each to
      for (const src of fromIds) {
        for (const tgt of toIds) {
          rfEdges.push({
            id: `${src}→${tgt}`,
            source: src,
            target: tgt,
            type: "smoothstep",
            animated: true,
            style: { stroke: "#3f3f46", strokeWidth: 1, strokeDasharray: "4 4" },
            markerEnd: { type: MarkerType.ArrowClosed, color: "#3f3f46", width: 10, height: 10 },
          })
        }
      }
    }
  }

  return { rfNodes, rfEdges }
}

export function WorkflowGraph() {
  const nodes = useAgentStore((s) => s.nodes)

  const { rfNodes, rfEdges } = useMemo(() => buildGraph(nodes), [nodes])

  // Use initial nodes/edges as key to force re-init
  const key = nodes.map((n) => n.id + n.status).join("|")

  return (
    <ReactFlow
      key={key}
      nodes={rfNodes as any}
      edges={rfEdges as any}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: 0.3 }}
      attributionPosition="bottom-left"
      proOptions={{ hideAttribution: true }}
    >
      <Background color="#27272a" gap={20} />
      <Controls className="!bg-zinc-800 !border-zinc-700 !rounded-lg [&>button]:!bg-zinc-700 [&>button]:!text-zinc-300 [&>button]:!border-zinc-600" />
      <MiniMap
        className="!bg-zinc-900 !border-zinc-700"
        maskColor="rgba(0,0,0,0.5)"
        nodeColor={(n) => {
          const status = (n as any)?.data?.status
          if (status === "running") return "#f59e0b"
          if (status === "done") return "#10b981"
          if (status === "error") return "#ef4444"
          return "#52525b"
        }}
      />
    </ReactFlow>
  )
}
