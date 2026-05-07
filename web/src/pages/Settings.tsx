import { useState, useEffect } from 'react'
import { Card, CardHeader, CardBody, Input, Select, SelectItem, Button, Divider, Chip, Spinner } from '@heroui/react'
import { FaSave, FaSync, FaMusic, FaDownload, FaFolder } from 'react-icons/fa'
import { api } from '../hooks/useApi'

const QUALITY_OPTIONS = [
  { value: '5', label: 'MP3 320kbps' },
  { value: '6', label: 'FLAC (16-bit / 44.1kHz) — CD Quality' },
  { value: '7', label: 'FLAC (Hi-Res ≤96kHz)' },
  { value: '27', label: 'FLAC (Hi-Res Ultra >96kHz)' },
]

export default function Settings() {
  const [settings, setSettings] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  async function loadSettings() {
    try {
      const data = await api.getSettings()
      setSettings(data)
    } catch (e) {
      console.error('Failed to load settings', e)
    } finally {
      setLoading(false)
    }
  }

  function updateSetting(key: string, value: string) {
    setSettings((prev) => ({ ...prev, [key]: value }))
    setSaved(false)
  }

  async function handleSave() {
    setSaving(true)
    try {
      await api.updateSettings(settings)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (e: any) {
      alert(e.message)
    } finally {
      setSaving(false)
    }
  }

  async function handleRefreshCredentials() {
    setRefreshing(true)
    try {
      const result = await api.refreshCredentials()
      if (result.app_id) {
        updateSetting('qobuz_app_id', result.app_id)
      }
      if (result.app_secret) {
        updateSetting('qobuz_app_secret', result.app_secret)
      }
    } catch (e: any) {
      alert(`Failed to refresh credentials: ${e.message}`)
    } finally {
      setRefreshing(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner color="primary" />
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Settings</h1>
          <p className="text-default-500 mt-1">Configure your Qobuz downloader</p>
        </div>
        <Button
          color="primary"
          startContent={saving ? <Spinner size="sm" /> : saved ? null : <FaSave />}
          isLoading={saving}
          isDisabled={saved}
          onPress={handleSave}
        >
          {saved ? 'Saved!' : 'Save All'}
        </Button>
      </div>

      {/* Qobuz Authentication */}
      <SectionCard icon={FaMusic} title="Qobuz Authentication">
        <div className="space-y-4">
          <Input
            label="Email"
            placeholder="your@email.com"
            value={settings.qobuz_email || ''}
            onChange={(e) => updateSetting('qobuz_email', e.target.value)}
            type="email"
          />
          <Input
            label="Password"
            placeholder="••••••••"
            value={settings.qobuz_password || ''}
            onChange={(e) => updateSetting('qobuz_password', e.target.value)}
            type="password"
            description="Leave empty if using Auth Token below"
          />
          <Input
            label="Auth Token"
            placeholder="Paste your Qobuz Auth Token here"
            value={settings.qobuz_auth_token || ''}
            onChange={(e) => updateSetting('qobuz_auth_token', e.target.value)}
            description="Alternative to email/password. Found in browser Local Storage under 'localuser' > 'token'"
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="App ID"
              value={settings.qobuz_app_id || ''}
              onChange={(e) => updateSetting('qobuz_app_id', e.target.value)}
              endContent={
                <Button isIconOnly size="sm" variant="light" onPress={handleRefreshCredentials} isLoading={refreshing}>
                  <FaSync className="text-sm" />
                </Button>
              }
            />
            <Input
              label="App Secret"
              value={settings.qobuz_app_secret || ''}
              onChange={(e) => updateSetting('qobuz_app_secret', e.target.value)}
            />
          </div>
          <p className="text-xs text-default-500">
            Click the refresh icon next to App ID to auto-extract credentials from Qobuz.
          </p>
        </div>
      </SectionCard>

      {/* Download Quality */}
      <SectionCard icon={FaDownload} title="Download Quality">
        <Select
          label="Audio Quality"
          selectedKeys={new Set([settings.qobuz_quality || '6'])}
          onChange={(e) => updateSetting('qobuz_quality', e.target.value)}
          className="max-w-md"
        >
          {QUALITY_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </Select>
      </SectionCard>

      {/* Output Configuration */}
      <SectionCard icon={FaFolder} title="Output Configuration">
        <div className="space-y-4">
          <Input
            label="Output Directory"
            placeholder="~/Music/Qobuz"
            value={settings.output_dir || ''}
            onChange={(e) => updateSetting('output_dir', e.target.value)}
          />
          <Input
            label="Folder Format"
            placeholder="{album_artist}/{album_title}"
            value={settings.folder_format || ''}
            onChange={(e) => updateSetting('folder_format', e.target.value)}
            description="Available: {album_artist}, {album_title}, {album_year}, {album_upc}"
          />
          <Input
            label="Filename Format"
            placeholder="{track_number:02d} - {title}"
            value={settings.filename_format || ''}
            onChange={(e) => updateSetting('filename_format', e.target.value)}
            description="Available: {track_number}, {title}, {artist}"
          />
          <div className="flex gap-4">
            <ToggleChip
              label="Skip existing files"
              active={settings.download_skip_existing !== 'false'}
              onToggle={(active) => updateSetting('download_skip_existing', String(active))}
            />
            <ToggleChip
              label="Download cover art"
              active={settings.download_covers !== 'false'}
              onToggle={(active) => updateSetting('download_covers', String(active))}
            />
            <ToggleChip
              label="Create M3U playlists"
              active={settings.download_m3u !== 'false'}
              onToggle={(active) => updateSetting('download_m3u', String(active))}
            />
          </div>
        </div>
      </SectionCard>
    </div>
  )
}

function SectionCard({ icon: Icon, title, children }: { icon: any; title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Icon className="text-primary" />
          <h2 className="text-lg font-semibold">{title}</h2>
        </div>
      </CardHeader>
      <Divider />
      <CardBody className="space-y-4">{children}</CardBody>
    </Card>
  )
}

function ToggleChip({ label, active, onToggle }: { label: string; active: boolean; onToggle: (active: boolean) => void }) {
  return (
    <button
      onClick={() => onToggle(!active)}
      className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
        active ? 'bg-primary/20 text-primary' : 'bg-default-200 text-default-500'
      }`}
    >
      <div className={`w-8 h-4 rounded-full relative transition-colors ${active ? 'bg-primary' : 'bg-default-400'}`}>
        <div className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform ${active ? 'translate-x-4' : 'translate-x-0'}`} />
      </div>
      {label}
    </button>
  )
}
