import { useState, useEffect } from 'react'
import { useParams } from '@tanstack/react-router'
import { Card, CardHeader, CardBody, Button, Spinner, Table, TableBody, TableCell, TableColumn, TableHeader, TableRow } from '@heroui/react'
import { FaMusic, FaDownload, FaClock } from 'react-icons/fa'
import { api, TrackItem } from '../hooks/useApi'

export default function PlaylistDetail() {
  const { playlistId } = useParams({ required: { playlistId: true } })
  const [tracks, setTracks] = useState<TrackItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [downloading, setDownloading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadTracks()
  }, [playlistId])

  async function loadTracks() {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getPlaylistTracks(playlistId)
      setTracks(data.tracks)
      setTotal(data.total)
    } catch (e: any) {
      setError(e.message || 'Failed to load tracks')
    } finally {
      setLoading(false)
    }
  }

  async function handleDownload() {
    setDownloading(true)
    try {
      await api.downloadPlaylist(playlistId)
    } catch (e: any) {
      alert(e.message)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Playlist Tracks</h1>
          <p className="text-default-500 mt-1">{total} tracks total</p>
        </div>
        <Button
          color="success"
          startContent={downloading ? <Spinner size="sm" /> : <FaDownload />}
          isLoading={downloading}
          onPress={handleDownload}
        >
          Download All
        </Button>
      </div>

      {error && (
        <Card className="bg-danger/10 border border-danger/30">
          <CardBody>
            <p className="text-danger text-sm">{error}</p>
          </CardBody>
        </Card>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <Spinner color="primary" />
        </div>
      ) : (
        <Card>
          <Table removeWrapper aria-label="Playlist tracks">
            <TableHeader>
              <TableColumn>#</TableColumn>
              <TableColumn>Title</TableColumn>
              <TableColumn>Artist</TableColumn>
              <TableColumn>Album</TableColumn>
              <TableColumn className="w-20">Duration</TableColumn>
            </TableHeader>
            <TableBody items={tracks}>
              {(track) => (
                <TableRow key={track.id}>
                  <TableCell>{track.track_number}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {track.album_image ? (
                        <img src={track.album_image} alt="" className="w-10 h-10 rounded object-cover" />
                      ) : (
                        <div className="w-10 h-10 rounded bg-default-200 flex items-center justify-center">
                          <FaMusic className="text-default-400" />
                        </div>
                      )}
                      <span className="font-medium">{track.title}</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-default-500">{track.artist}</TableCell>
                  <TableCell className="text-default-500">{track.album}</TableCell>
                  <TableCell>
                    <span className="flex items-center gap-1 text-sm text-default-500">
                      <FaClock className="text-xs" />
                      {track.duration_formatted}
                    </span>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  )
}
