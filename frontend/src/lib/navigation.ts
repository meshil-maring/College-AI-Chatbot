import { useSyncExternalStore } from 'react'

function subscribe(onChange: () => void) {
  window.addEventListener('popstate', onChange)
  return () => window.removeEventListener('popstate', onChange)
}

function locationSnapshot() {
  return `${window.location.pathname}${window.location.search}`
}

export function useBrowserLocation() {
  const location = useSyncExternalStore(subscribe, locationSnapshot)
  const separator = location.indexOf('?')
  return separator === -1
    ? { pathname: location, search: '' }
    : { pathname: location.slice(0, separator), search: location.slice(separator) }
}

/** Notify route subscribers for app navigation as well as browser Back/Forward. */
export function navigateTo(path: string, options: { replace?: boolean } = {}) {
  if (path === locationSnapshot()) return
  if (options.replace) window.history.replaceState(null, '', path)
  else window.history.pushState(null, '', path)
  window.dispatchEvent(new PopStateEvent('popstate'))
}
