import { useState, useEffect, useRef } from 'react'
import { Card, CardHeader, CardBody, Button, Select, SelectItem, Spinner } from '@heroui/react'
import { FaTerminal, FaTrash, FaArrowDown } from 'react-icons/fa'
import { api, LogEntry } from '../hooks/useApi'

export default function Logs() {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('ALL')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadLogs()
    const interval = setInterval(loadLogs, 3000)
    return () => clearInterval(interval)
  }, [filter])

  async function loadLogs() {
    try {
      const data = await api.getLogs(200)
      const filtered = filter === 'ALL' ? data : data.filter((l) => l.level === filter)
      setLogs(filtered)
    } catch (e) {
      console.error('Failed to load logs', e)
    } finally {
      setLoading(false)
    }
  }

  async function handleClear() {
    if (confirm('Clear logs older than 7 days?')) {
      await api.clearLogs(7)
      loadLogs()
    }
  }

  const levelColors: Record<string, string> = {
    INFO: 'text-blue-400',
    WARNING: 'text-yellow-400',
    ERROR: 'text-red-400',
    DEBUG: 'text-gray-400',
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Logs</h1>
          <p className="text-default-500 mt-1">Application activity log</p>
        </div>
        <div className="flex gap-2">
          <Select
            label="Filter"
            selectedKeys={new Set([filter])}
            onChange={(e) => setFilter(e.target.value)}
            className="w-40"
            size="sm"
          >
            <SelectItem key="ALL">All</SelectItem>
            <SelectItem key="INFO">Info</SelectItem>
            <SelectItem key="WARNING">Warning</SelectItem>
            <SelectItem key="ERROR">Error</SelectItem>
          </Select>
          <Button size="sm" isIconOnly variant="light" onPress={handleClear}>
            <FaTrash />
          </Button>
        </div>
      </div>

      <Card className="bg-default-50/50">
        <CardBody className="p-0">
          <div className="max-h-[600px] overflow-y-auto font-mono text-xs p-4 bg-black/20 rounded-b-lg">
            {loading ? (
              <div className="flex justify-center py-12">
                <Spinner color="primary" size="sm" />
              </div>
            ) : (
              <>
                {logs.map((log) => (
                  <div key={log.id} className="flex gap-3 py-1 hover:bg-white/5 rounded px-2 -mx-2">
                    <span className="text-default-500 shrink-0">{log.timestamp}</span>
                    <span className={`shrink-0 font-bold w-16 ${levelColors[log.level] || 'text-default-400'}`}>
                      [{log.level}]
                    </span>
                    <span className="text-default-300">{log.message}</span>
                  </div>
                ))}
                <div ref={bottomRef} />
              </>
            )}
          </div>
        </CardBody>
      </Card>
    </div>
  )
}
