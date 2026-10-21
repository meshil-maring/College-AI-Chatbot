import { inputClass, labelClass, Section } from './InstitutionSection.tsx'
import type { InstitutionDetailPanelModel } from './useInstitutionDetail.ts'
export function InstitutionBasicInformation({ model }: { model: InstitutionDetailPanelModel }) {
  const { name, setName, code, setCode, saving, saveConfiguration } = model
  return (
    <Section title="Basic Information">
      <div className="grid gap-5 lg:grid-cols-2">
        <div>
          <label className={labelClass} htmlFor="detail-name">
            Institution name
          </label>
          <input
            id="detail-name"
            className={inputClass}
            value={name}
            onChange={(event) => {
              setName(event.target.value)
            }}
          />
        </div>
        <div>
          <label className={labelClass} htmlFor="detail-code">
            Institution code
          </label>
          <input
            id="detail-code"
            className={inputClass}
            value={code}
            onChange={(event) => {
              setCode(event.target.value)
            }}
          />
          <p className="mt-1 text-xs text-slate-500">
            Changing this changes the public URL. Existing codes are never rewritten silently.
          </p>
        </div>
      </div>
      <div className="mt-5">
        <button
          type="button"
          onClick={() => {
            void saveConfiguration()
          }}
          disabled={saving}
          className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-300 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save changes'}
        </button>
      </div>
    </Section>
  )
}
