import { useMemo } from "react"
import {
  ReactFlow,
  Background,
  type Node,
  type Edge,
  MarkerType,
} from "@xyflow/react"
import { useAgentStore } from "../../stores/agentStore"
import { TOOL_REGISTRY, type ToolNodeData } from "../../types/agent"
import { ToolNode } from "./ToolNode"

const nodeTypes = { toolNode: ToolNode }

function buildToolDAG(
  records: { tool_name: string; status: string; latency_ms: number }[],
): { rfNodes: Node<ToolNodeData>[]; rfEdges: Edge[] } {
  const tools = Object.values(TOOL_REGISTRY)
  const recordMap = new Map(records.map((r) => [r.tool_name, r]))

  // Group by layer
  const layers: Record<number, string[]> = {}
  for (const t of tools) {
    (layers[t.layer] ??= []).push(t.name)
  }

  const rfNodes: Node<ToolNodeData>[] = tools.map((t) => {
    const rec = recordMap.get(t.name)
    return {
      id: t.name,
      type: "toolNode",
      position: { x: 0, y: 0 },
      data: {
        name: t.name,
        human_readable_name: t.human_readable_name,
        layer: t.layer,
        status: (rec?.status as ToolNodeData["status"]) ?? "pending",
        is_idempotent: t.is_idempotent,
        physical_impact: t.physical_impact,
        latency_ms: rec?.latency_ms,
      },
    }
  })

  // Layout
  const LAYER_X_GAP = 200
  const NODE_Y_GAP = 60
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

  // Edges from dependencies
  const rfEdges: Edge[] = []
  for (const t of tools) {
    for (const dep of t.dependencies) {
      rfEdges.push({
        id: `${dep}→${t.name}`,
        source: dep,
        target: t.name,
        type: "smoothstep",
        style: { stroke: "#3f3f46", strokeWidth: 1 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#3f3f46", width: 10, height: 10 },
      })
    }
  }

  return { rfNodes, rfEdges }
}

export function ExecutionDAG() {
  const executionState = useAgentStore((s) => s.executionState)
  const records = executionState?.tool_records ?? []

  const { rfNodes, rfEdges } = useMemo(() => buildToolDAG(records), [records])

  const key = records.map((r) => r.tool_name + r.status).join("|")

  if (records.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-xs text-zinc-600">
        Tool execution state will appear here after plan confirmation
      </div>
    )
  }

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
      <Background color="#27272a" gap={16} />
    </ReactFlow>
  )
}
