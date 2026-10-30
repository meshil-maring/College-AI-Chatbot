import { useLayoutEffect, useRef } from 'react'

/** Keep the selected tab readable inside a horizontally scrolling tab list. */
export function useVisibleTab(value: string) {
  const ref = useRef<HTMLDivElement>(null)
  useLayoutEffect(() => {
    const list = ref.current
    if (!list) return
    function reveal() {
      const selected = list?.querySelector<HTMLElement>('[role="tab"][aria-selected="true"]')
      if (!list || !selected) return
      const bounds = list.getBoundingClientRect()
      const tab = selected.getBoundingClientRect()
      if (tab.left < bounds.left) list.scrollLeft -= bounds.left - tab.left
      else if (tab.right > bounds.right) list.scrollLeft += tab.right - bounds.right
    }
    reveal()
    const observer = typeof ResizeObserver === 'undefined' ? undefined : new ResizeObserver(reveal)
    observer?.observe(list)
    return () => observer?.disconnect()
  }, [value])
  return ref
}
