import type Anthropic from "@anthropic-ai/sdk";

export const TOOL_DEFINITIONS: Anthropic.Tool[] = [
  {
    name: "list_tables",
    description: "List all available Delta tables with schema and version info.",
    input_schema: { type: "object", properties: {}, required: [] },
  },
  {
    name: "get_schema",
    description: "Return column names and data types for a specific Delta table.",
    input_schema: {
      type: "object",
      properties: {
        table_name: {
          type: "string",
          description: "The name of the table (use list_tables to see available names).",
        },
      },
      required: ["table_name"],
    },
  },
  {
    name: "sample_data",
    description: "Return the first N rows of a Delta table (default 10, max 100).",
    input_schema: {
      type: "object",
      properties: {
        table_name: { type: "string", description: "The name of the table." },
        n: {
          type: "integer",
          description: "Number of rows to return (default 10, max 100).",
          default: 10,
        },
      },
      required: ["table_name"],
    },
  },
  {
    name: "query_table",
    description:
      "Execute a SQL query over Delta tables using DuckDB. " +
      "Reference tables by their short name (e.g. SELECT * FROM oag_may LIMIT 5). " +
      "Default cap is 100 rows — include LIMIT in SQL for more (max 1000).",
    input_schema: {
      type: "object",
      properties: {
        sql: { type: "string", description: "SQL query to execute." },
      },
      required: ["sql"],
    },
  },
];

export const SYSTEM_PROMPT = `You are ClearPath, a data analyst assistant for Southwest Airlines operational decision-making.
You have access to airline scheduling, aircraft rotation, and fare analysis data via Delta Lake tables.

Use the provided tools to answer questions accurately. Guidelines:
- Always call list_tables first if you're unsure what data is available.
- Use get_schema before querying a table you haven't seen before.
- Present tabular data as markdown tables when showing results.
- Be concise and focus on actionable insights relevant to airline operations.
- For NOC and operational questions, prioritize revenue impact and operational feasibility.`;
