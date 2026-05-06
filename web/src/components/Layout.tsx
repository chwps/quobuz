import { Link, Outlet, useLocation } from '@tanstack/react-router'
import { Navbar, NavbarBrand, NavbarContent, NavbarItem } from '@heroui/react'
import { FaMusic, FaList, FaCog, FaTerminal, FaPlus } from 'react-icons/fa'

const navItems = [
  { label: 'Dashboard', path: '/', icon: FaMusic },
  { label: 'Playlists', path: '/playlists', icon: FaList },
  { label: 'Settings', path: '/settings', icon: FaCog },
  { label: 'Logs', path: '/logs', icon: FaTerminal },
]

export function Layout() {
  const { pathname } = useLocation()

  return (
    <div className="min-h-screen bg-background">
      <Navbar
        maxWidth="full"
        height="64"
        className="bg-background/80 backdrop-blur border-b border-default-200"
        classNames={{
          wrapper: 'max-w-7xl w-full',
        }}
      >
        <NavbarBrand>
          <div className="flex items-center gap-2">
            <FaMusic className="text-2xl text-primary" />
            <span className="text-xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
              Quobuz
            </span>
          </div>
        </NavbarBrand>

        <NavbarContent justify="center">
          {navItems.map((item) => (
            <NavbarItem key={item.path} isActive={pathname === item.path}>
              <Link
                to={item.path}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                  pathname === item.path
                    ? 'text-primary bg-primary/10'
                    : 'text-default-500 hover:text-foreground hover:bg-default-100'
                }`}
              >
                <item.icon className="text-sm" />
                <span className="text-sm font-medium">{item.label}</span>
              </Link>
            </NavbarItem>
          ))}
        </NavbarContent>

        <NavbarContent justify="end">
          <NavbarItem>
            <Link to="/playlists/new">
              <button className="flex items-center gap-1 px-3 py-1.5 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors">
                <FaPlus className="text-xs" />
                Add Playlist
              </button>
            </Link>
          </NavbarItem>
        </NavbarContent>
      </Navbar>

      <main className="max-w-7xl mx-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
