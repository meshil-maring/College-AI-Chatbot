/** Recover unmistakable numbered sections in answers saved before line breaks were preserved. */
export function prepareAnswerMarkdown(content: string): string {
  if (/[\r\n`]/.test(content)) return content
  const sections = [...content.matchAll(/(^|[ \t]+)(\d+)\.[ \t]+(\*\*[^*\n]{1,140}\*\*:?[ \t]*)/g)]
  if (sections.length < 2 || sections.some((section, index) => Number(section[2]) !== index + 1)) return content

  const blocks = [content.slice(0, sections[0].index).trim()]
  sections.forEach((section, index) => {
    const body = content.slice(section.index + section[0].length, sections[index + 1]?.index ?? content.length).trim()
    const heading = `${section[2]}. ${section[3].trim()}`
    if (!body.startsWith('- ')) {
      blocks.push(`${heading} ${body}`.trim())
      return
    }
    const indent = ' '.repeat(section[2].length + 2)
    const items = body.slice(2).split(/(?<=[.!?])[ \t]+-[ \t]+(?=[\p{L}\d])/u)
    blocks.push(`${heading}\n${items.map((item) => `${indent}- ${item}`).join('\n')}`)
  })
  return blocks.filter(Boolean).join('\n\n')
}
