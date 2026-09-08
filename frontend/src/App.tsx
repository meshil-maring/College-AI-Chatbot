import { AuthProvider, useAuth } from './features/auth/AuthProvider.tsx'
import LoginForm from './features/auth/LoginForm.tsx'
import ChatShell from './features/chat/ChatShell.tsx'

function RestoringShell() {
  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <main className="max-w-xl w-full text-center py-16">
        <div className="rounded-2xl border border-slate-700 bg-slate-800 p-10 shadow-xl">
          <h1 className="text-4xl font-bold text-white tracking-tight">College AI Chatbot</h1>
          <p className="mt-4 text-lg text-slate-300">Restoring your session…</p>
        </div>
      </main>
    </div>
  )
}

function AuthenticatedShell() {
  return <ChatShell />
}

function AuthGate() {
  const { status } = useAuth()
  if (status === 'restoring') {
    return <RestoringShell />
  }
  if (status === 'authenticated') {
    return <AuthenticatedShell />
  }
  return <LoginForm />
}

function App() {
  return (
    <AuthProvider>
      <AuthGate />
    </AuthProvider>
  )
}

export default App
