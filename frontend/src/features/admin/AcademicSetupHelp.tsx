import { useId, useState } from 'react'
import { Info } from 'lucide-react'

/** Hover, keyboard focus and tapping all expose the same short explanation. */
export default function AcademicSetupHelp({ label, children }: { label: string; children: string }) {
  const id = useId()
  const [hovered, setHovered] = useState(false)
  const [focused, setFocused] = useState(false)
  const [pinned, setPinned] = useState(false)
  const [dismissed, setDismissed] = useState(false)
  const visible = !dismissed && (hovered || focused || pinned)

  return <span className="relative inline-flex" onMouseEnter={() => { setHovered(true); setDismissed(false) }} onMouseLeave={() => setHovered(false)}>
    <button
      type="button" aria-label={`Help for ${label}`} aria-describedby={visible ? id : undefined} aria-expanded={visible}
      className="inline-flex h-7 w-7 items-center justify-center rounded-full text-slate-400 hover:bg-slate-700 hover:text-emerald-300 focus:outline-none focus:ring-2 focus:ring-emerald-400"
      onFocus={() => { setFocused(true); setDismissed(false) }}
      onBlur={() => { setFocused(false); setPinned(false); setDismissed(false) }}
      onClick={() => { setPinned(!pinned); setDismissed(pinned) }}
      onKeyDown={(event) => { if (event.key === 'Escape') { setPinned(false); setDismissed(true); event.stopPropagation() } }}
    ><Info className="h-4 w-4" aria-hidden="true" /></button>
    {visible ? <span id={id} role="tooltip" className="absolute -left-12 bottom-full z-20 mb-2 w-56 max-w-[calc(100vw-3rem)] rounded-lg border border-slate-500 bg-slate-950 p-3 text-left text-xs font-normal leading-relaxed text-slate-100 shadow-xl sm:left-0">{children}</span> : null}
  </span>
}
