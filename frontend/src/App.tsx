import { useEffect, useState } from "react";

function App() {
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((res) => res.json())
      .then((data) => setStatus(data.status))
      .catch(() => setStatus("error"));
  }, []);

  const isOk = status === "ok";

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-950 text-white">
      <h1 className="text-5xl font-bold tracking-tight">Chorus</h1>
      <p className="mt-3 text-lg text-gray-400">
        Project management for humans and AI
      </p>
      <div className="mt-6 flex items-center gap-2 text-sm">
        <span
          className={`inline-block h-2.5 w-2.5 rounded-full ${
            status === null
              ? "bg-gray-500"
              : isOk
                ? "bg-green-500"
                : "bg-red-500"
          }`}
        />
        <span className="text-gray-400">
          {status === null
            ? "Checking backend..."
            : isOk
              ? "Backend: ok"
              : "Backend: unreachable"}
        </span>
      </div>
    </div>
  );
}

export default App;
