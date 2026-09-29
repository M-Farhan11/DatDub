import { useEffect, useMemo } from "react"
import {
  Background,
  BackgroundVariant,
  Controls,
  ReactFlow,
  ReactFlowProvider,
  useNodesState,
  useReactFlow,
  type Edge,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import type { DatasetSchema } from "@/api/types"
import type { ColumnRef } from "@/state/studioReducer"
import { SchemaGraphContext } from "./graphContext"
import { layoutTables, structureKey } from "./graphLayout"
import { relationLabel } from "./schemaText"
import { TableNode, type TableNodeType } from "./TableNode"

const nodeTypes = { table: TableNode }

interface SchemaGraphProps {
  schema: DatasetSchema
  selected: ColumnRef | null
  onSelect: (ref: ColumnRef) => void
}

function buildNodes(schema: DatasetSchema): TableNodeType[] {
  const positions = layoutTables(schema)
  return schema.tables.map((t) => ({
    id: t.name,
    type: "table",
    position: positions.get(t.name) ?? { x: 0, y: 0 },
    data: { tableName: t.name },
  }))
}

function buildEdges(schema: DatasetSchema): Edge[] {
  const names = new Set(schema.tables.map((t) => t.name))
  const edges: Edge[] = []
  for (const table of schema.tables) {
    for (const fk of table.foreign_keys) {
      if (!names.has(fk.ref_table)) continue
      edges.push({
        id: `${table.name}.${fk.column}->${fk.ref_table}.${fk.ref_column}`,
        source: fk.ref_table,
        sourceHandle: `${fk.ref_column}-out`,
        target: table.name,
        targetHandle: `${fk.column}-in`,
        type: "smoothstep",
        label: relationLabel(fk, table.name),
        style: { stroke: "var(--primary)", strokeWidth: 1.25 },
        labelStyle: { fill: "var(--ink-muted)", fontSize: 11.5, fontWeight: 500, fontFamily: "Inter, sans-serif" },
        labelBgStyle: { fill: "var(--card)" },
        labelBgPadding: [6, 3],
        labelBgBorderRadius: 6,
      })
    }
  }
  return edges
}

function Graph({ schema, selected, onSelect }: SchemaGraphProps) {
  const key = structureKey(schema)
  const [nodes, setNodes, onNodesChange] = useNodesState<TableNodeType>(buildNodes(schema))
  const { fitView } = useReactFlow()

  // Re-layout only when tables or links change; column edits keep dragged positions.
  useEffect(() => {
    setNodes(buildNodes(schema))
    requestAnimationFrame(() => void fitView({ padding: 0.12, maxZoom: 1 }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const edges = useMemo(() => buildEdges(schema), [key])
  const tables = useMemo(() => new Map(schema.tables.map((t) => [t.name, t])), [schema])
  const ctx = useMemo(() => ({ tables, selected, onSelect }), [tables, selected, onSelect])

  return (
    <SchemaGraphContext.Provider value={ctx}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        fitView
        fitViewOptions={{ padding: 0.12, maxZoom: 1 }}
        minZoom={0.3}
        maxZoom={1.6}
        nodesConnectable={false}
        edgesFocusable={false}
        proOptions={{ hideAttribution: true }}
        aria-label="Schema graph"
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="var(--line)" />
        <Controls showInteractive={false} position="bottom-left" />
      </ReactFlow>
    </SchemaGraphContext.Provider>
  )
}

export function SchemaGraph(props: SchemaGraphProps) {
  return (
    <ReactFlowProvider>
      <Graph {...props} />
    </ReactFlowProvider>
  )
}
