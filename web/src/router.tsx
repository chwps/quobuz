import { createRouter, createRootRoute, createRoute } from '@tanstack/react-router'
import { Layout } from './components/Layout'
import Dashboard from './pages/Dashboard'
import Playlists from './pages/Playlists'
import PlaylistDetail from './pages/PlaylistDetail'
import Settings from './pages/Settings'
import Logs from './pages/Logs'

const rootRoute = createRootRoute()

const layoutRoute = createRoute({
  getParentRoute: () => rootRoute,
  component: Layout,
  id: 'layout',
})

const dashboardRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/',
  component: Dashboard,
})

const playlistsRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/playlists',
  component: Playlists,
})

const playlistDetailRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/playlists/$playlistId',
  component: PlaylistDetail,
})

const settingsRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/settings',
  component: Settings,
})

const logsRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/logs',
  component: Logs,
})

const routeTree = rootRoute.addChildren([layoutRoute.addChildren([
  dashboardRoute,
  playlistsRoute,
  playlistDetailRoute,
  settingsRoute,
  logsRoute,
])])

export const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface RegisterRouter {
    router: typeof router
  }
}
