import { inputClass, labelClass, Section } from './InstitutionSection.tsx'
import type { InstitutionDetailPanelModel } from './useInstitutionDetail.ts'
export function InstitutionBranding({ model }: { model: InstitutionDetailPanelModel }) {
  const { displayName, setDisplayName, welcomeMessage, setWelcomeMessage, primaryColor, setPrimaryColor } = model
  return (
    <Section title="Branding">
      <div className="grid gap-5 lg:grid-cols-2">
        <div>
          <label className={labelClass} htmlFor="detail-display">
            Display name
          </label>
          <input
            id="detail-display"
            className={inputClass}
            value={displayName}
            onChange={(event) => {
              setDisplayName(event.target.value)
            }}
            placeholder="Falls back to the institution name"
          />
        </div>
        <div>
          <label className={labelClass} htmlFor="detail-color">
            Primary colour
          </label>
          <input
            id="detail-color"
            className={inputClass}
            value={primaryColor}
            onChange={(event) => {
              setPrimaryColor(event.target.value)
            }}
            placeholder="#0F172A"
          />
        </div>
        <div className="lg:col-span-2">
          <label className={labelClass} htmlFor="detail-welcome">
            Welcome message
          </label>
          <input
            id="detail-welcome"
            className={inputClass}
            value={welcomeMessage}
            onChange={(event) => {
              setWelcomeMessage(event.target.value)
            }}
            placeholder="Shown on the public institution gateway"
          />
        </div>
      </div>
    </Section>
  )
}
