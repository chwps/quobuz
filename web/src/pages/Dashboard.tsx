import { useState, useEffect } from 'react'
import { Card, CardHeader, CardBody } from '@heroui/react'
import { FaMusic, FaSync, FaDownload, FaCheck } from 'react-icons/fa'
import { api, Job, Subscription, Playlist } from '../hooks/useApi'

export default function Dashboard() {
  const [playlists, setPlaylists] = useState<Playlist[]>([])
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([])
  const [activeJobs, setActiveJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboard()
    const interval = setInterval(loadDashboard, 5000)
    return () => clearInterval(interval)
  }, [])

  async function loadDashboard() {
    try {
      const [pls, subs, jobs] = await Promise.all([
        api.getPlaylists(),
        api.getSubscriptions(),
        api.getActiveJobs(),
      ])
      setPlaylists(pls)
      setSubscriptions(subs)
      setActiveJobs(jobs)
    } catch {
      // silently fail — not authenticated yet
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-default-500 mt-1">Monitor your Qobuz downloads</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard icon={FaMusic} label="Playlists" value={playlists.length} />
        <StatCard icon={FaSync} label="Subscribed" value={subscriptions.length} />
        <StatCard icon={FaDownload} label="Active Jobs" value={activeJobs.length} />
        <StatCard icon={FaCheck} label="Completed" value="—" />
      </div>

      {/* Active Jobs */}
      {activeJobs.length > 0 && (
        <Card className="bg-default-50">
          <CardHeader>
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <FaDownload className="text-primary animate-pulse" />
              Active Downloads
            </h2>
          </CardHeader>
          <CardBody>
            {activeJobs.map((job) => (
              <div key={job.id} className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-default-600">{job.current_track || 'Starting...'}</span>
                  <span className="font-medium">{job.progress.toFixed(1)}%</span>
                </div>
                <div className="w-full bg-default-200 rounded-full h-2">
                  <div
                    className="bg-primary h-2 rounded-full transition-all duration-300"
                    style={{ width: `${job.progress}%` }}
                  />
                </div>
                <div className="flex gap-4 text-xs text-default-500">
                  <span>↓ {job.downloaded}</span>
                  <span>⏭ {job.skipped}</span>
                  <span>✗ {job.failed}</span>
                  <span>total: {job.total_tracks}</span>
                </div>
              </div>
            ))}
          </CardBody>
        </Card>
      )}

      {/* Subscriptions */}
      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <FaSync className="text-secondary" />
            Subscriptions
          </h2>
        </CardHeader>
        <CardBody>
          {subscriptions.length === 0 ? (
            <p className="text-default-500 text-sm">No subscriptions yet. Go to Playlists to subscribe.</p>
          ) : (
            <div className="space-y-2">
              {subscriptions.map((sub) => (
                <div key={sub.playlist_qobuz_id} className="flex justify-between items-center p-3 rounded-lg bg-default-50">
                  <div>
                    <p className="font-medium text-sm">{sub.title}</p>
                    <p className="text-xs text-default-500">
                      {sub.download_count} downloads · Last: {sub.last_downloaded || 'never'}
                    </p>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full ${sub.active ? 'bg-success/20 text-success' : 'bg-default-200 text-default-500'}`}>
                    {sub.active ? 'Active' : 'Paused'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  )
}

function StatCard({ icon: Icon, label, value }: { icon: any; label: string; value: string | number }) {
  return (
    <Card className="bg-default-50">
      <CardBody className="flex flex-row items-center gap-4">
        <div className="p-3 rounded-xl bg-primary/10 text-primary">
          <Icon className="text-xl" />
        </div>
        <div>
          <p className="text-2xl font-bold">{value}</p>
          <p className="text-sm text-default-500">{label}</p>
        </div>
      </CardBody>
    </Card>
  )
}
