export default function WorkspacePageHeader({
  title,
  description,
  eyebrow = 'Institution workspace',
}: {
  title: string
  description?: string
  eyebrow?: string
}) {
  return (
    <div className="ui-page-header">
      <div>
        <p className="ui-eyebrow">{eyebrow}</p>
        <h1 className="text-page font-bold text-content">{title}</h1>
        {description && <p className="ui-description">{description}</p>}
      </div>
    </div>
  )
}
