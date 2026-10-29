import './mockSetup.ts'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LearningResourcesPage from '../LearningResourcesPage.tsx'

export function renderResources(
  client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } }),
) {
  const tree = () => (
    <QueryClientProvider client={client}>
      <LearningResourcesPage />
    </QueryClientProvider>
  )
  const view = render(tree())
  return { ...view, client, user: userEvent.setup(), replaceIdentity: () => view.rerender(tree()) }
}
export async function openDraft(user: ReturnType<typeof userEvent.setup>) {
  await screen.findByText('Published handbook')
  await user.click(screen.getByRole('button', { name: 'My submissions', exact: true }))
  await user.click(await screen.findByRole('button', { name: 'View Library guide' }))
  const dialog = await screen.findByRole('dialog')
  await within(dialog).findByRole('textbox', { name: 'Title' })
  return within(dialog)
}
