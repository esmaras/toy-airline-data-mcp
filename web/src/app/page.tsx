import ChatInterface from "@/components/ChatInterface";

export default function Home() {
  return (
    <main className="flex flex-col h-screen">
      <header className="bg-blue-700 text-white px-6 py-3 flex items-center gap-3 shadow">
        <span className="text-xl font-bold tracking-tight">ClearPath</span>
        <span className="text-blue-200 text-sm">Southwest Airlines Data Assistant</span>
      </header>
      <div className="flex-1 overflow-hidden">
        <ChatInterface />
      </div>
    </main>
  );
}
