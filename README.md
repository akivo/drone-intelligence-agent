# Drone Fleet Intelligence Agent

![Python](https://img.shields.io/badge/Python-3.13-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-multi--agent-green)
![LangChain](https://img.shields.io/badge/LangChain-RAG-orange)
![AirSim](https://img.shields.io/badge/AirSim-drone--sim-lightgrey)
![Groq](https://img.shields.io/badge/Groq-Llama--3.3--70B-purple)
![Docker](https://img.shields.io/badge/Docker-deployed-blue)

A multi-agent AI co-pilot for Microsoft AirSim drones. Reads live telemetry every 2 seconds, autonomously detects flight anomalies, stores every snapshot in a vector database, and answers natural language questions over full flight history — all with a human-in-the-loop gate before any critical action executes.

---

## Demo

> **[Watch demo video](#)** — AirSim drone on the left, live agent terminal on the right

*(Replace `#` with your unlisted YouTube link after recording)*

---

## Architecture

```
AirSim Simulator
      |  live telemetry (every 2s)
      v
 Monitor Agent  ---anomaly?---> HITL Gate (human y / n / e)
 (LangGraph)                         |
      |  every snapshot              v
      v                       Approve / Cancel / Escalate
 flight_logger --> pgvector (PostgreSQL + vector embeddings)
                         |
                         v
                  RAG Query Agent  <-- natural language question
                  (LangChain LCEL)  --> answer in < 2s via Groq
                         |
                         v
                   LangSmith  (traces every agent run)
```

---

## Tech Stack

| Layer | Tool | Why |
|---|---|---|
| Simulation | Microsoft AirSim | Industry-standard drone sim; same stack serious UAV teams use |
| Agent orchestration | LangGraph | Stateful multi-agent graph with conditional routing to HITL |
| LLM | Groq — Llama 3.3-70B | Free tier, fastest inference available, no credit card needed |
| Embeddings | HuggingFace all-MiniLM-L6-v2 | Runs fully locally — no API key, no cost |
| Vector store | pgvector (PostgreSQL) | Persistent flight log memory with similarity search |
| Observability | LangSmith | Full audit trail — inputs, decisions, latency, token usage |
| Deployment | Docker + docker-compose | One-command deploy; runs on AWS EC2 |

---

## Agents

| Agent | File | What it does |
|---|---|---|
| Monitor Agent | [agents/monitor_agent.py](agents/monitor_agent.py) | LangGraph graph — reads telemetry, detects LOW_BATTERY / ALTITUDE_BREACH / OVERSPEED |
| HITL Gate | [agents/hitl_gate.py](agents/hitl_gate.py) | Pauses graph, waits for human y / n / e before any critical action |
| RAG Query Agent | [agents/rag_query_agent.py](agents/rag_query_agent.py) | Answers natural language questions over stored flight logs |

---

## FlytBase JD Alignment

| Requirement | Implementation |
|---|---|
| Multi-agent framework | LangGraph `StateGraph` with conditional edges across Monitor + RAG agents |
| RAG pipeline + persistent memory | LangChain LCEL + pgvector — every telemetry snapshot embedded and stored |
| Autonomous function execution | Monitor agent calls detection tools autonomously every 2s cycle |
| Human-in-the-loop safety | HITL gate hard-pauses graph; no action executes without operator input |
| Observability | `@traceable` on every node; full traces in LangSmith dashboard |
| Cloud deployment | Dockerfile + docker-compose; deploys to AWS EC2 in one command |
| Vision / sensor perception | AirSim camera feed available via `client.simGetImages()` |

---

## Anomaly Detection

The monitor agent flags three conditions and routes them to the HITL gate:

| Anomaly | Threshold | Proposed Action |
|---|---|---|
| LOW_BATTERY | battery < 20% | RETURN_TO_HOME |
| ALTITUDE_BREACH | altitude > 100m | DESCEND_TO_SAFE_ALTITUDE |
| OVERSPEED | speed > 20 m/s | REDUCE_SPEED |

---

## Sample RAG Queries

After a flight, ask in plain English:

```
"What was the maximum altitude reached during the flight?"
"Were there any battery warnings during the patrol?"
"How many anomalies were detected and what types were they?"
"What was the average speed throughout the flight?"
"Summarize the patrol route telemetry."
```

---

## Setup

### Prerequisites

- Python 3.13
- AirSim prebuilt binary — [github.com/microsoft/AirSim/releases](https://github.com/microsoft/AirSim/releases) (download `Blocks.zip`, choose drone mode)
- Groq API key — free at [console.groq.com](https://console.groq.com)
- LangSmith API key — free at [smith.langchain.com](https://smith.langchain.com)
- Docker Desktop (for pgvector)

### 1. Clone and install

```bash
git clone https://github.com/yourusername/drone-fleet-intelligence-agent
cd drone-fleet-intelligence-agent
pip install -r requirements.txt
```

### 2. Configure environment

```bash
copy .env.example .env
# Fill in GROQ_API_KEY and LANGCHAIN_API_KEY
```

### 3. Configure AirSim

Create `C:\Users\<you>\Documents\AirSim\settings.json`:

```json
{
  "SettingsVersion": 1.2,
  "SimMode": "Multirotor",
  "Vehicles": {
    "Drone1": { "VehicleType": "SimpleFlight", "AutoCreate": true }
  }
}
```

### 4. Start the database

```bash
docker-compose up db -d
```

### 5. Run

```bash
python main.py
```

The agent auto-detects whether AirSim is running. If not, it falls back to a realistic mock client — all agent logic (LangGraph, HITL, RAG, LangSmith) works identically either way.

---

## Manual Flight

Fly the drone yourself via keyboard while AirSim is open:

```bash
python fly_manual.py
```

| Key | Action |
|---|---|
| T | Takeoff |
| W / S | Forward / Backward |
| A / D | Left / Right |
| R / F | Up / Down |
| Q / E | Rotate left / right |
| X | Hover |
| L | Land |
| ESC | Land and quit |

---

## Docker (full stack)

```bash
docker-compose up --build
```

AirSim runs locally; the agent + pgvector run in containers.

---

## AWS Deployment

```bash
# On EC2 Ubuntu 22.04 (t2.micro free tier)
sudo apt-get install -y docker.io docker-compose
git clone https://github.com/yourusername/drone-fleet-intelligence-agent
cd drone-fleet-intelligence-agent
nano .env          # paste your API keys
docker-compose up -d
```

---

## Observability

Every agent node is decorated with `@traceable`. Open your LangSmith dashboard to see the full trace for every cycle:

- Telemetry ingested per cycle
- Anomaly detection decision + reason
- HITL gate input / operator response
- RAG retrieval results + LLM answer
- Token usage and latency per run

*(Add LangSmith screenshot here)*
