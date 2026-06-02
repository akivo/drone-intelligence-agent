# Drone Fleet Intelligence Agent — Personal Interview Handbook

---

# PART 1 — PROJECT DEEP DIVE

## What Is This Project?

This is a multi-agent AI system that acts as an intelligent co-pilot for drones. It connects to Microsoft AirSim (a photorealistic drone simulator), reads live telemetry data every 2 seconds, and makes intelligent decisions about the drone's safety — all while keeping a human in the loop for critical actions.

Think of it like an air traffic controller that never sleeps: it watches every number coming off the drone, understands when something is wrong, decides what to do about it, asks a human before acting, remembers everything that happened, and can answer questions about past flights in plain English.

---

## The Problem It Solves

Real drone operators face three core problems:
1. **Too much data** — a drone sends 20+ telemetry values per second. No human can watch all of them.
2. **Delayed reaction** — by the time a human notices a low battery, it may be too late to return safely.
3. **No memory** — after a flight, the raw logs are hard to query. "When did battery first drop below 30%?" takes manual log parsing.

This system solves all three: agents watch the data, anomaly detection fires instantly, and the RAG pipeline makes the full flight history queryable in natural language.

---

## System Components — Detailed

### 1. AirSim Simulator
Microsoft AirSim is an open-source drone simulator built on Unreal Engine. It runs a full physics simulation — gravity, wind resistance, motor dynamics — and exposes a Python API for reading state (position, velocity, GPS, battery) and sending commands (takeoff, move, land).

Our `AirSimClient` connects via TCP to the running simulator. If AirSim is not running, the `MockAirSimClient` generates mathematically realistic synthetic telemetry (sine-wave altitude, linear battery decay) so the entire agent stack can be developed and tested without a running simulator.

### 2. Monitor Agent (LangGraph)
The monitor agent is a directed graph built with LangGraph's `StateGraph`. A graph is the right tool here because the monitoring pipeline has conditional branching — normal telemetry takes one path, anomalies take another.

**Graph nodes:**
- `ingest_node` — receives raw telemetry dict, prints it to terminal
- `detect_node` — applies rule-based thresholds (battery < 20%, altitude > 100m, speed > 20 m/s)
- `log_node` — reached only if no anomaly; logs "All systems nominal"

**Graph edges:**
- `ingest → detect` (always)
- `detect → hitl` (if anomaly detected) — ends the graph, control passes to HITL
- `detect → log` (if nominal) — logs and ends

Every node is decorated with `@traceable` so LangSmith captures the full execution.

### 3. HITL Gate (Human-in-the-Loop)
When the monitor agent detects an anomaly, it does NOT automatically act. Instead it calls `hitl_gate()` which:
- Prints the full alert context (anomaly type, proposed action, current telemetry)
- Blocks execution and waits for operator input
- Accepts three responses: `y` (approve), `n` (cancel), `e` (escalate)
- Returns the updated state with `approved=True/False`

This is the safety-critical design pattern used in real autonomous systems. No irreversible action happens without human confirmation.

### 4. Flight Logger (pgvector)
Every telemetry snapshot — regardless of whether an anomaly occurred — is converted to a natural language sentence and embedded using HuggingFace's `all-MiniLM-L6-v2` model (384-dimensional vectors). This embedding is stored in PostgreSQL via the pgvector extension.

Example stored text:
```
Drone Drone1 at 2026-06-01T18:55:13: altitude 16.0m, battery 98%, speed 4.8m/s,
position (37.7749, -122.4194), flying=True
```

This converts structured time-series telemetry into semantically searchable text — enabling the RAG pipeline.

### 5. RAG Query Agent (LangChain + Groq)
After a flight, operators can ask questions in plain English. The RAG agent:
1. Embeds the question using the same HuggingFace model
2. Retrieves the 10 most semantically similar log entries from pgvector
3. Passes retrieved context + question to Groq's Llama 3.3-70B
4. Returns a factual answer grounded in the actual flight data

This is Retrieval-Augmented Generation — the LLM never guesses; it only answers from retrieved evidence.

### 6. Observability (LangSmith)
Every function decorated with `@traceable` sends its execution data to LangSmith:
- Function name, inputs, outputs
- Execution time (latency)
- Token usage (for LLM calls)
- Parent-child relationships (which call triggered which)

This creates a full audit trail for every monitoring cycle — essential for debugging agent behavior and demonstrating compliance.

---

## Data Flow — End to End

```
1. main.py starts
2. AirSim connects (or MockAirSimClient activates)
3. Patrol task starts (async background)
4. Monitor loop starts (async, runs concurrently)
5. Every 2 seconds:
   a. get_telemetry() → TelemetrySnapshot
   b. monitor_graph.invoke(snapshot) → LangGraph runs
   c. If anomaly: hitl_gate(result) → wait for human
   d. log_telemetry(snapshot) → embed + store in pgvector
6. After 30 cycles (60 seconds):
7. run_demo_queries() → 5 RAG questions answered from pgvector
8. Session ends
```

---

## Key Design Decisions

**Why LangGraph instead of a simple loop?**
LangGraph makes the control flow explicit and traceable. The graph structure enforces that detect always follows ingest, and HITL is the only path for anomalies. A plain Python loop could do the same logic but wouldn't give you the visual trace, state management, or easy extensibility.

**Why pgvector instead of a regular database?**
Telemetry logs are structured numbers. To query them in natural language ("when did altitude exceed 80m?"), you need semantic similarity search, not SQL. pgvector stores the text embedding alongside the data, enabling the RAG pipeline. A regular SQL query could answer exact questions but couldn't handle paraphrased natural language.

**Why Groq + Llama instead of OpenAI?**
Groq provides free inference on open-source Llama 3.3-70B with the fastest token generation in the industry (700+ tokens/second). For this use case — answering questions over retrieved text — it is equivalent to GPT-4o-mini at zero cost.

**Why HuggingFace embeddings instead of OpenAI embeddings?**
`all-MiniLM-L6-v2` runs entirely locally, produces 384-dimensional vectors, and is specifically trained for semantic similarity tasks. OpenAI embeddings cost money per token and require a network call. For telemetry text that follows a predictable pattern, local embeddings perform equally well.

**Why MockAirSimClient?**
AirSim requires Windows, a powerful GPU, and a running binary. A mock client lets the entire agent stack be developed, tested, and demonstrated on any machine. The mock generates realistic data (sine-wave altitude, linear battery decay) rather than random numbers, so the agents behave identically in both modes.

---

# PART 2 — INTERVIEW QUESTIONS & ANSWERS

---

## SECTION A — BASIC / WARM-UP QUESTIONS

**Q: Can you explain this project in one sentence?**
A: It's a multi-agent AI system that monitors a drone in real time, detects safety anomalies, requires human approval before acting, and answers natural language questions over flight history using RAG.

**Q: Why did you build this project?**
A: To demonstrate the skills directly required for the FlytBase Agentic AI Engineer role — multi-agent orchestration, RAG pipelines, human-in-the-loop safety, and observability — applied to a drone context that is directly relevant to the company's product.

**Q: What is AirSim?**
A: Microsoft AirSim is an open-source photorealistic drone and car simulator built on Unreal Engine. It exposes a Python API for reading telemetry (position, velocity, GPS, camera) and sending control commands. It is used by serious drone AI teams for simulation-to-reality transfer.

**Q: What does "telemetry" mean in this context?**
A: Telemetry is the real-time stream of sensor data from the drone — altitude, battery percentage, GPS coordinates, speed, and whether it is flying or grounded. It is read every 2 seconds and fed into the monitor agent.

**Q: What happens when AirSim is not running?**
A: The `get_client()` factory function in `simulation/airsim_client.py` catches the connection error and returns a `MockAirSimClient` instead. This mock generates mathematically realistic synthetic telemetry and supports the full patrol sequence, so the entire agent stack works without a running simulator.

**Q: What is a HITL gate?**
A: Human-in-the-loop (HITL) gate is a design pattern where an AI system pauses execution at a critical decision point and waits for a human to approve, cancel, or escalate before proceeding. In this project, it fires whenever the monitor agent detects a LOW_BATTERY, ALTITUDE_BREACH, or OVERSPEED anomaly.

**Q: What anomalies does the system detect?**
A: Three: LOW_BATTERY (battery below 20%), ALTITUDE_BREACH (altitude above 100 metres), and OVERSPEED (speed above 20 m/s). Each triggers a different proposed action — return to home, descend, or reduce speed respectively.

---

## SECTION B — LANGGRAPH QUESTIONS

**Q: What is LangGraph?**
A: LangGraph is a library built on top of LangChain for building stateful, multi-step agent applications as directed graphs. Each node is a function, edges define control flow, and a shared `State` dict is passed through the graph. It supports conditional routing, cycles (loops), and interrupts (for HITL).

**Q: Why use a graph instead of a simple if-else in Python?**
A: Three reasons: (1) The graph structure is explicit and visualisable — anyone can see the control flow. (2) LangGraph integrates with LangSmith for automatic tracing of every node execution. (3) It makes the system extensible — adding a new agent (e.g. a GPS anomaly detector) means adding a new node, not refactoring conditionals.

**Q: What is `StateGraph` and `AgentState`?**
A: `StateGraph` is LangGraph's graph builder class. `AgentState` is a `TypedDict` that defines all fields the graph can read and write — telemetry, anomaly_detected, anomaly_type, proposed_action, needs_approval, approved, log_message. Every node receives the full state and returns an updated copy.

**Q: How does conditional routing work in the graph?**
A: `add_conditional_edges(source_node, routing_function, mapping)`. The routing function takes the current state and returns a string key. The mapping dict maps that key to the next node name. In our graph: `route_after_detect` returns `"hitl"` if `needs_approval` is True, otherwise `"log"`.

**Q: What does `END` mean in LangGraph?**
A: `END` is a special terminal node. When the graph reaches `END`, execution stops and the final state is returned to the caller. In our graph, the HITL path routes directly to `END` because control passes out of the graph to `hitl_gate()`.

**Q: What is a `@traceable` decorator?**
A: It is a LangSmith decorator that wraps a function and automatically sends its name, inputs, outputs, and execution time to the LangSmith tracing backend. No code change is needed beyond adding the decorator — tracing is automatic.

**Q: Can LangGraph handle cycles (loops)?**
A: Yes. LangGraph supports cycles in the graph, which enables retry loops and iterative refinement patterns. Our current graph is a DAG (no cycles), but you could add a cycle from `log` back to `ingest` to create a continuous monitoring loop without the external Python `for` loop.

---

## SECTION C — RAG PIPELINE QUESTIONS

**Q: What is RAG?**
A: Retrieval-Augmented Generation. Instead of relying on the LLM's training data to answer questions, RAG first retrieves relevant documents from an external knowledge base, then passes those documents as context to the LLM. This grounds the LLM's answer in real, up-to-date data and prevents hallucination.

**Q: Why is RAG the right approach for querying flight logs?**
A: Flight logs are dynamic, timestamped data that did not exist when the LLM was trained. Without RAG, the LLM would hallucinate answers. With RAG, every answer is grounded in the actual retrieved log entries from the current flight — the LLM acts as a reasoning engine over real evidence.

**Q: What is pgvector?**
A: pgvector is a PostgreSQL extension that adds a `vector` data type and similarity search operators. It allows storing high-dimensional floating-point vectors alongside regular data and querying them using cosine, L2, or inner product distance. It turns PostgreSQL into a vector database.

**Q: Why use pgvector instead of a dedicated vector database like Pinecone or Weaviate?**
A: pgvector runs inside PostgreSQL, which we already need for structured data storage. It avoids a separate service, reduces infrastructure complexity, and is free and self-hosted. For production at scale, a dedicated vector DB might be preferred — but for this use case pgvector is the right trade-off.

**Q: What is an embedding?**
A: An embedding is a numerical representation of text as a fixed-length vector of floating-point numbers. Similar texts produce vectors that are close together in vector space (low cosine distance). We embed telemetry text so that semantically similar log entries (e.g. "battery 18%" and "battery 19%") can be retrieved together.

**Q: What embedding model is used and why?**
A: `all-MiniLM-L6-v2` from HuggingFace sentence-transformers. It produces 384-dimensional vectors, runs locally (no API call), is fast, and is specifically trained on semantic similarity tasks. It is a strong baseline for retrieval over short, structured text like telemetry.

**Q: What is LangChain LCEL?**
A: LCEL (LangChain Expression Language) is a declarative syntax for composing chains using the `|` pipe operator. Example: `{"context": retriever | format_docs, "question": passthrough} | prompt | llm | parser`. It is the modern replacement for legacy chain classes like `RetrievalQA` and makes the pipeline more readable and composable.

**Q: What does `k=10` mean in the retriever?**
A: It means retrieve the 10 most similar documents from pgvector for each query. We increased it from 5 to 10 to ensure the retriever covers both the flying phase and the grounded phase of the flight, improving answer quality for queries about the full flight history.

**Q: What is cosine similarity in the context of vector search?**
A: Cosine similarity measures the angle between two vectors — if they point in the same direction, similarity is 1.0 (identical). If perpendicular, similarity is 0. For text embeddings, high cosine similarity means the texts are semantically related. pgvector uses this to find the most relevant log entries for a query.

**Q: How does the RAG chain answer a question like "Were there any battery warnings?"**
A: (1) The question is embedded into a 384-dimensional vector. (2) pgvector finds the 10 most similar log entries (those mentioning battery levels). (3) Those 10 log texts are concatenated as context. (4) The prompt template wraps them: "You are a drone analyst. Answer using only this context: {context}. Question: {question}". (5) Groq's Llama 3.3-70B generates a factual answer from the retrieved evidence.

**Q: What prevents the LLM from hallucinating in this RAG system?**
A: The system prompt instructs the model: "Answer the question using only the flight log context below." The model is given explicit evidence and told not to go beyond it. Additionally, the retrieved logs are factual telemetry numbers — there is little room for creative interpretation.

---

## SECTION D — VECTOR DATABASE & POSTGRESQL QUESTIONS

**Q: What is the schema of the flight_logs table?**
A: `id` (serial primary key), `timestamp` (timestamptz), `drone_id` (text), `content` (text — the natural language log), `embedding` (vector(384) — the HuggingFace embedding). The `vector` column type comes from the pgvector extension.

**Q: How is telemetry converted to text before embedding?**
A: In `flight_logger.py`, the `_snapshot_to_text()` function formats the snapshot dict into a natural language sentence: "Drone Drone1 at 2026-06-01T18:55:13: altitude 16.0m, battery 98%, speed 4.8m/s, position (37.7749, -122.4194), flying=True". This text is what gets embedded and stored.

**Q: Why convert structured data to natural language for embedding?**
A: Embedding models are trained on natural language text, not structured JSON. Converting telemetry to a readable sentence means the embedding captures semantic meaning — "battery 15%" and "battery critical" will have similar embeddings, enabling fuzzy retrieval. A raw JSON blob would embed poorly.

**Q: What is the difference between `add_documents()` and `similarity_search()`?**
A: `add_documents()` embeds each document and inserts it into pgvector (write path). `similarity_search(query, k=10)` embeds the query and finds the k nearest documents by cosine distance (read path). Both are methods on the `PGVector` LangChain object.

---

## SECTION E — OBSERVABILITY & LANGSMITH QUESTIONS

**Q: What is LangSmith?**
A: LangSmith is Anthropic's (LangChain's) observability platform for LLM applications. It captures traces of every agent run — what went in, what came out, how long it took, how many tokens were used, and the parent-child relationships between calls. It is essential for debugging and auditing agentic systems.

**Q: What does a LangSmith trace contain for this project?**
A: For each 2-second cycle: the `ingest_telemetry` trace (input telemetry dict, output state), the `detect_anomaly` trace (input state, output with anomaly flags), and if HITL fired, the `hitl_approval_gate` trace (input anomaly context, output with approved flag). For RAG queries: the `rag_query` trace shows the question, retrieved context, and LLM answer.

**Q: Why is observability important for agentic systems specifically?**
A: Agents make autonomous decisions that can have real-world consequences. Without observability you cannot answer: Why did the agent take action X? Was the HITL gate bypassed? What data led to a wrong answer? LangSmith provides the audit trail that makes agentic behavior explainable and auditable.

**Q: How do you configure LangSmith tracing?**
A: Set three environment variables: `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY=<your key>`, `LANGCHAIN_PROJECT=<project name>`. LangChain and LangGraph automatically detect these and send traces. The `configure_langsmith()` function in our code validates these are set and prints the dashboard URL.

---

## SECTION F — ASYNC / ARCHITECTURE QUESTIONS

**Q: Why does main.py use `asyncio.gather(patrol_task, monitor_task)`?**
A: The drone patrol and the telemetry monitoring need to run concurrently. `asyncio.gather()` runs both coroutines in the same event loop simultaneously — the patrol moves the drone while the monitor reads and processes telemetry. Without concurrency, monitoring would block during patrol or vice versa.

**Q: What is the difference between `asyncio.create_task()` and `await coroutine()`?**
A: `await coroutine()` runs sequentially — the caller waits for it to complete. `asyncio.create_task()` schedules the coroutine to run concurrently in the background. We use `create_task` for both patrol and monitor so they run in parallel, then `await gather()` to wait for both to finish.

**Q: Why is `monitor_graph.invoke()` called synchronously inside an async function?**
A: `monitor_graph.invoke()` is a synchronous LangGraph call. Since it completes in milliseconds (pure Python rule evaluation), there is no benefit to making it async. For longer-running agent calls (e.g. LLM calls), you would use `monitor_graph.ainvoke()` to avoid blocking the event loop.

**Q: What is a `dataclass` and why is `TelemetrySnapshot` one?**
A: A `dataclass` is a Python class that auto-generates `__init__`, `__repr__`, and other methods from field annotations. `TelemetrySnapshot` is a dataclass because telemetry is pure data — no methods, no logic. The `to_dict()` method converts it to a plain dict for LangGraph state, since `StateGraph` works with dicts.

---

## SECTION G — DOCKER & DEPLOYMENT QUESTIONS

**Q: What does docker-compose.yml do in this project?**
A: It defines two services: `db` (pgvector/pgvector:pg16 — PostgreSQL with vector extension pre-installed) and `agent` (our Python application). The agent depends on the db service being healthy before starting. A shared `pgdata` volume persists the database between restarts.

**Q: What is the `init.sql` file for?**
A: It runs automatically when the pgvector container first starts. It creates the `vector` extension and the `flight_logs` table with a `vector(384)` column. This ensures the database is schema-ready before the agent connects.

**Q: Why is the vector dimension 384 in the schema?**
A: Because `all-MiniLM-L6-v2` produces 384-dimensional embeddings. The pgvector column type must match the embedding dimension exactly. If you switched to OpenAI embeddings (1536-dim), you would need to update the schema to `vector(1536)`.

**Q: What is the difference between Docker and docker-compose?**
A: Docker builds and runs a single container. docker-compose orchestrates multiple containers as a single application — defining their configuration, dependencies, networks, and volumes in one `docker-compose.yml` file. One command (`docker-compose up`) starts the entire stack.

**Q: How would you deploy this to AWS EC2?**
A: Launch a t2.micro Ubuntu 22.04 instance (free tier), SSH in, install docker and docker-compose, clone the GitHub repo, create the `.env` file with API keys, and run `docker-compose up -d`. The agent and pgvector run in containers. AirSim runs on the local machine and connects to the agent via the network.

---

## SECTION H — PYTHON & CODE QUESTIONS

**Q: What is a `TypedDict` and why use it for `AgentState`?**
A: `TypedDict` is a Python type hint class that defines the expected keys and value types of a dictionary. LangGraph requires state to be a dict (for serialisation), but `TypedDict` adds type safety and IDE autocomplete. It is the recommended pattern for LangGraph state definitions.

**Q: How does the anomaly detection work at a code level?**
A: In `detect_node()`, we read `state["telemetry"]` and check three conditions with if-else. The first matching condition returns an updated state dict with `anomaly_detected=True`, `anomaly_type`, `proposed_action`, and `needs_approval=True`. If none match, it returns `anomaly_detected=False`. This is rule-based detection, not ML-based.

**Q: Why is `_get_vectorstore()` implemented with a global variable and lazy initialisation?**
A: Creating a `PGVector` object establishes a database connection. We don't want to connect on import (the DB might not be running). Lazy initialisation means we only connect when `log_telemetry()` is first called. The global `_vectorstore` caches the connection so subsequent calls reuse it.

**Q: What is the `backports.ssl_match_hostname` shim and why was it needed?**
A: `msgpack-rpc-python` (AirSim's RPC transport) depends on `tornado 4.5.3`, which imports `backports.ssl_match_hostname` — a module that existed for Python 2/early Python 3 compatibility but was removed in Python 3.12+. We created a stub implementation in site-packages that provides the required functions using the modern `ssl` module, satisfying the import without changing any third-party code.

**Q: Why use `msvcrt.getwch()` in fly_manual.py?**
A: `msvcrt` is a Windows-only module that reads a single keypress immediately without requiring Enter to be pressed. This gives the interactive flight controller instant response — pressing `W` immediately moves the drone without needing to confirm with Enter. On Linux/Mac, you would use `tty` and `termios` instead.

---

## SECTION I — AI/ML THEORY QUESTIONS

**Q: What is the difference between RAG and fine-tuning?**
A: Fine-tuning trains the model weights on your specific data — expensive, requires retraining for new data. RAG retrieves relevant documents at inference time and passes them as context — cheap, works with new data immediately, no training required. For dynamic data like flight logs, RAG is always the right choice.

**Q: What is a vector database and when would you use one?**
A: A vector database stores high-dimensional float vectors and supports approximate nearest-neighbour search. Use it when you need semantic similarity search — finding documents that are conceptually similar to a query, not exact string matches. Use cases: RAG, recommendation systems, image search, anomaly detection.

**Q: What is the difference between a vector database and a regular database for this use case?**
A: A regular database can answer "SELECT * WHERE battery_pct < 20" (exact/range queries). A vector database can answer "find flight logs similar to 'critical battery situation'" even if those exact words don't appear in the logs. RAG needs the semantic search capability that only a vector database provides.

**Q: What is the difference between semantic search and keyword search?**
A: Keyword search (like SQL LIKE or Elasticsearch) finds documents containing the exact query words. Semantic search finds documents with similar meaning even if they use different words — "battery critical" and "low charge" would match semantically even though no words overlap. Embeddings enable semantic search.

**Q: What is an LLM agent?**
A: An LLM agent is an AI system that uses a language model not just to generate text, but to make decisions, call tools, and take actions in a loop. Instead of a single input-output call, the agent observes state, reasons about what to do, calls a tool (e.g. search, code execution), observes the result, and repeats until the task is done.

**Q: What is the difference between a chain and an agent in LangChain?**
A: A chain has a fixed sequence of steps — input goes through step A, then B, then C, always in the same order. An agent is dynamic — it uses an LLM to decide which step to take next, can loop, can call different tools based on context. Our monitor agent is a graph-based agent; the RAG query is a chain.

**Q: What is temperature in LLMs and what did we set it to?**
A: Temperature controls randomness in LLM output. Temperature 0 = deterministic (always picks the most likely token). Higher temperature = more creative/random. We set temperature to 0 because we want factual, consistent answers from the flight log data — not creative variation.

**Q: What are tokens in the context of LLMs?**
A: Tokens are the basic units an LLM processes — roughly 3-4 characters or 0.75 words in English. "Low battery warning" is about 4 tokens. LLMs have a context window (max tokens they can process at once) and are billed by token count. LangSmith tracks token usage per call.

---

## SECTION J — SYSTEM DESIGN QUESTIONS

**Q: How would you scale this system to monitor 100 drones simultaneously?**
A: Run one monitor agent instance per drone as a separate async task (or process). Use a message queue (Redis Streams or Kafka) to collect telemetry from all drones. Use a single shared pgvector database. The HITL gate would need a dashboard (Slack/web UI) rather than terminal input. LangSmith scales automatically.

**Q: How would you make the HITL gate work in production?**
A: Replace the `input()` call with a webhook or message queue. When an anomaly fires, send a Slack message or push notification to the operator's phone with the alert details and Approve/Cancel buttons. The agent waits (with a timeout) for a response. If no response within N seconds, default to the safe action (e.g. return to home).

**Q: What happens if the database goes down during a flight?**
A: The `log_telemetry()` call is wrapped in a `try/except` in `main.py`. If pgvector is unreachable, it prints `[WARN] Could not log to pgvector` and continues. The monitor agent and HITL gate are unaffected — they run entirely in memory. The only loss is the telemetry not being stored for later RAG queries.

**Q: How would you add a new anomaly type, for example GPS signal loss?**
A: In `detect_node()` in `monitor_agent.py`, add a new `if` block: check `snapshot["gps_quality"] < threshold`, set `anomaly_type = "GPS_LOSS"`, `proposed_action = "HOLD_POSITION"`, `needs_approval = True`. No other code needs changing — the HITL gate and logger handle any anomaly type generically.

**Q: How would you replace rule-based anomaly detection with ML-based detection?**
A: Train an anomaly detection model (Isolation Forest, LSTM autoencoder, or a classifier) on historical flight data. In `detect_node()`, replace the if-else thresholds with a call to `model.predict(telemetry_features)`. The rest of the pipeline — HITL gate, logging, RAG — is unchanged because `detect_node` only needs to return a state with `anomaly_detected` and `anomaly_type`.

**Q: How would you handle a situation where the HITL operator is unavailable?**
A: Add a timeout to the HITL gate — if no response within 30 seconds, execute the conservative default action automatically (e.g. return to home). Log this as an "auto-approved" event with a flag. Alert a secondary operator. This is standard practice in safety-critical autonomous systems.

**Q: What is the latency of one full monitoring cycle?**
A: The bottleneck is pgvector write — typically 50-100ms. The LangGraph execution (rule evaluation) is under 5ms. The full cycle including sleep is 2 seconds. RAG queries take 500ms-1s depending on Groq response time. Overall, the system is well within real-time requirements for drone monitoring.

---

## SECTION K — BEHAVIORAL / PROJECT QUESTIONS

**Q: What was the hardest technical problem you faced?**
A: The `airsim` package on PyPI does not build on Python 3.13 because it depends on `msgpack-rpc-python` which requires `tornado 4.5.3`, which in turn imports `backports.ssl_match_hostname` — a module removed in Python 3.12. The solution was to download the AirSim Python client files directly from GitHub (bypassing pip build) and create a `backports.ssl_match_hostname` stub in site-packages.

**Q: Why did the RAG answer say "flying=False" when the drone was flying?**
A: A timing mismatch — the mock patrol lasted 14 seconds but the monitor loop ran for 60 seconds. So 23 of 30 logged snapshots had `flying=False` (grounded phase). The k=5 similarity search retrieved grounded logs for most queries. Fixed by extending patrol legs from 3s to 12s each, making the drone fly for 50 of 60 seconds.

**Q: What would you add next if you had more time?**
A: (1) A web dashboard replacing the terminal HITL gate — React frontend with real-time telemetry graphs and approve/deny buttons. (2) ML-based anomaly detection replacing hardcoded thresholds. (3) Multi-drone support with a fleet overview. (4) AirSim camera feed integration — object detection on the drone's live video. (5) Automated test suite with simulated anomaly scenarios.

**Q: How does this project relate to FlytBase's actual product?**
A: FlytBase builds fleet management software for commercial drones. This project demonstrates the agentic AI layer that could sit on top of such a platform — reading telemetry from FlytBase's APIs, detecting fleet-wide anomalies, asking for operator approval via the FlytBase dashboard, and enabling natural language querying of fleet history. The architecture maps directly to their tech stack.

**Q: What did you learn from building this?**
A: The importance of graceful degradation — the mock client means the system is always runnable regardless of environment. LangChain's API changes frequently (connection_string → connection, embedding_function → positional arg) so pinning versions and reading changelogs is critical. And observability is not optional — LangSmith traces were essential for understanding why RAG answers were wrong.

---

## SECTION L — QUICK FIRE DEFINITIONS

| Term | One-line Definition |
|---|---|
| LangGraph | Library for building stateful multi-agent graphs with conditional routing |
| LangChain | Framework for building LLM applications with chains, tools, and retrieval |
| LangSmith | Observability platform for tracing LLM application runs |
| pgvector | PostgreSQL extension adding vector similarity search |
| RAG | Retrieval-Augmented Generation — ground LLM answers in retrieved documents |
| HITL | Human-in-the-loop — pause AI execution for human approval |
| Embedding | Fixed-length float vector representing text meaning |
| Cosine similarity | Measure of angle between two vectors — used for semantic search |
| AirSim | Microsoft open-source drone simulator built on Unreal Engine |
| StateGraph | LangGraph class for building directed graphs with shared state |
| LCEL | LangChain Expression Language — pipe operator syntax for building chains |
| Temperature 0 | LLM setting for deterministic, non-random output |
| `@traceable` | LangSmith decorator that captures function I/O for observability |
| asyncio | Python library for writing concurrent code with async/await |
| docker-compose | Tool for defining and running multi-container Docker applications |
| MockAirSimClient | Fallback client that generates synthetic telemetry when AirSim is unavailable |

---

## SECTION M — NUMBERS TO REMEMBER

| Metric | Value |
|---|---|
| Telemetry interval | Every 2 seconds |
| Monitoring cycles | 30 cycles = 60 seconds |
| Battery threshold (alert) | Below 20% |
| Altitude threshold (alert) | Above 100 metres |
| Speed threshold (alert) | Above 20 m/s |
| Embedding dimensions | 384 (all-MiniLM-L6-v2) |
| RAG retrieval count | k = 10 nearest neighbours |
| Patrol waypoints | 4 (box pattern) |
| Patrol duration | ~50 seconds (12s per leg) |
| Battery decay | 3.5% per cycle |
| Anomaly first fires | Cycle 23 (battery hits ~19%) |

---

*Good luck with the interview. You built every line of this — you know it better than anyone asking about it.*
