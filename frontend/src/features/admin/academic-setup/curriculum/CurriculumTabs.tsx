export default function CurriculumTabs<T extends string>({
  items,
  value,
  onChange,
  prefix,
  label,
}: {
  items: readonly { id: T; label: string }[]
  value: T
  onChange: (value: T) => void
  prefix: string
  label: string
}) {
  return (
    <div className="curriculum-tabs" role="tablist" aria-label={label}>
      {items.map((item, index) => (
        <button
          type="button"
          role="tab"
          key={item.id}
          id={`${prefix}-${item.id}`}
          aria-selected={value === item.id}
          aria-controls={`${prefix}-panel`}
          tabIndex={value === item.id ? 0 : -1}
          onClick={() => onChange(item.id)}
          onKeyDown={(event) => {
            let next = index
            if (event.key === 'ArrowRight') next = (index + 1) % items.length
            else if (event.key === 'ArrowLeft') next = (index + items.length - 1) % items.length
            else if (event.key === 'Home') next = 0
            else if (event.key === 'End') next = items.length - 1
            else return
            event.preventDefault()
            onChange(items[next].id)
            document.getElementById(`${prefix}-${items[next].id}`)?.focus()
          }}
        >
          {item.label}
        </button>
      ))}
    </div>
  )
}
