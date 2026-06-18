type ToolName = "list_tables" | "get_schema" | "sample_data" | "query_table";

export async function callTool(
  toolName: ToolName,
  args: Record<string, unknown>
): Promise<string> {
  const SHARING_SERVER_URL = process.env.SHARING_SERVER_URL;
  if (!SHARING_SERVER_URL) {
    throw new Error("SHARING_SERVER_URL environment variable is not set");
  }
  const url = `${SHARING_SERVER_URL}/tools/${toolName}`;

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(args),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Tool '${toolName}' failed (${res.status}): ${text}`);
  }

  const data = await res.json();
  return data.result as string;
}
