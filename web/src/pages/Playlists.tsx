import { useState, useEffect } from 'react'
import { Link } from '@tanstack/react-router'
import { Card, CardHeader, CardBody, Button, Spinner, Input, Chip } from '@heroui/react'
import { FaMusic, FaSync, FaDownload, FaPlus, FaSearch } from 'react-icons/fa'
import { api, Playlist } from '../hooks/useApi'

export default function Playlists() {
  const [playlists, setPlaylists] = useState<Playlist[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [downloading, setDownloading] = useState<string | null>(null)

  useEffect(() => {
    loadPlaylists()
  }, [])

  async function loadPlaylists() {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getPlaylists()
      setPlaylists(data)
    } catch (e: any) {
      setError(e.message || 'Failed to load playlists')
    } finally {
      setLoading(false)
    }
  }

  async function handleSubscribe(id: string) {
    try {
      await api.subscribePlaylist(id)
      setPlaylists((prev) =>
        prev.map((p) => (p.qobuz_id === id ? { ...p, is_subscribed: true } : p))
      )
    } catch (e: any) {
      alert(e.message)
    }
  }

  async function handleUnsubscribe(id: string) {
    try {
      await api.unsubscribePlaylist(id)
      setPlaylists((prev) => prev.filter((p) => p.qobuz_id !== id))
    } catch (e: any) {
      alert(e.message)
    }
  }

  async function handleDownload(id: string) {
    setDownloading(id)
    try {
      await api.downloadPlaylist(id)
    } catch (e: any) {
      alert(e.message)
    } finally {
      setDownloading(null)
    }
  }

  const filtered = playlists.filter(
    (p) =>
      p.title.toLowerCase().includes(search.toLowerCase()) ||
      p.creator.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Playlists</h1>
          <p className="text-default-500 mt-1">Browse your Qobuz playlists</p>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-default-400" />
        <Input
          placeholder="Search playlists..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          classNames={{ inputWrapper: 'rounded-xl' }}
          className="max-w-md"
        />
      </div>

      {/* Error */}
      {error && (
        <Card className="bg-danger/10 border border-danger/30">
          <CardBody>
            <p className="text-danger text-sm">{error}</p>
            <Button size="sm" color="danger" variant="light" className="mt-2" onPress={loadPlaylists}>
              Retry
            </Button>
          </CardBody>
        </Card>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex justify-center py-12">
          <Spinner color="primary" />
        </div>
      )}

      {/* Playlist Grid */}
      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((pl) => (
            <Card key={pl.qobuz_id} className="overflow-hidden hover:shadow-lg transition-shadow">
              <Link to={`/playlists/${pl.qobuz_id}`}>
                <div className="aspect-video bg-gradient-to-br from-primary/20 to-secondary/20 flex items-center justify-center">
                  {pl.image ? (
                    <img src={pl.image} alt={pl.title} className="w-full h-full object-cover" />
                  ) : (
                    <FaMusic className="text-4xl text-default-400" />
                  )}
                </div>
              </Link>
              <CardBody className="space-y-3">
                <div>
                  <Link to={`/playlists/${pl.qobuz_id}`}>
                    <h3 className="font-semibold text-foreground hover:text-primary transition-colors line-clamp-2">
                      {pl.title}
                    </h3>
                  </Link>
                  <p className="text-sm text-default-500 mt-1">by {pl.creator || 'Qobuz'}</p>
                </div>

                <div className="flex gap-2 text-xs text-default-500">
                  <Chip size="sm" variant="flat">{pl.track_count} tracks</Chip>
                  <Chip size="sm" variant="flat">{pl.duration_formatted}</Chip>
                  {pl.follower_count > 0 && (
                    <Chip size="sm" variant="flat">{pl.follower_count} followers</Chip>
                  )}
                </div>

                <div className="flex gap-2">
                  {pl.is_subscribed ? (
                    <Button
                      size="sm"
                      color="primary"
                      variant="flat"
                      startContent={<FaSync />}
                      onPress={() => handleUnsubscribe(pl.qobuz_id)}
                    >
                      Unsubscribe
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      color="primary"
                      variant="flat"
                      startContent={<FaPlus />}
                      onPress={() => handleSubscribe(pl.qobuz_id)}
                    >
                      Subscribe
                    </Button>
                  )}
                  <Button
                    size="sm"
                    color="success"
                    variant="flat"
                    startContent={downloading === pl.qobuz_id ? <Spinner size="sm" /> : <FaDownload />}
                    onPress={() => handleDownload(pl.qobuz_id)}
                    isLoading={downloading === pl.qobuz_id}
                  >
                    Download
                  </Button>
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      {!loading && filtered.length === 0 && (
        <div className="text-center py-12 text-default-500">
          <FaMusic className="text-4xl mx-auto mb-4 opacity-50" />
          <p>No playlists found</p>
        </div>
      )}
    </div>
  )
}
