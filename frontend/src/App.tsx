function App() {
  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4">
      <main className="max-w-xl w-full text-center py-16">
        <div className="rounded-2xl border border-slate-700 bg-slate-800 p-10 shadow-xl">
          <h1 className="text-4xl font-bold text-white tracking-tight">
            College AI Chatbot
          </h1>
          <p className="mt-4 text-lg text-slate-300 leading-relaxed">
            A grounded Q&amp;A assistant for college policies — powered by the
            FastAPI retrieval and generation backend.
          </p>
          <div className="mt-8 inline-flex items-center gap-2 rounded-full bg-emerald-900/50 px-4 py-1.5 text-sm font-medium text-emerald-300 border border-emerald-700">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            Frontend foundation ready
          </div>
        </div>
        <p className="mt-8 text-xs text-slate-500">
          Phase 5.2 scaffold — chat interface arrives in a later phase.
        </p>
      </main>
    </div>
  )
}

export default App
