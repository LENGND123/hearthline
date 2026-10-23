# Hearthline

Hearthline is an Alexa+ coach for the air around one household. You tell it the city and who lives there. It remembers children and asthma across sessions, checks the live air, and speaks a plan for the school morning or the evening.

The plan is specific: outdoor PE or a short one, windows open or shut, a mask for pickup, or an hour of night air and then close up. The answer changes with the US AQI band and with who is in the home.

This is a submission for the [Build, Ship, Shape: Amazon Developer Hackathon](https://amazonappdev2026.devpost.com/) on the **Alexa+** track. The open-source mini challenge uses this same repository: https://github.com/LENGND123/hearthline

## How it fits the track

The coach is a self-hosted MCP server on Streamable HTTP. A fresh client negotiates protocol **2025-11-25**. The web page is the simulated Alexa+ experience: a voice-style turn, a spoken reply, and a card.

The page never reads the household file and never calls the air API. Each turn opens an MCP session and calls tools.

| Tool | What it does |
| --- | --- |
| `remember_household` | Saves the city or one person. Call it once per person. |
| `get_household` | Reads the saved home, including the last plan. |
| `check_air` | Live air for a city, or for the saved home if you leave the city blank. |
| `plan_day` | Builds the school, evening, outdoor, or right-now plan and saves it. |
| `save_routine` | Stores a named routine on the household. |
| `recall_history` | Returns the plans saved earlier. |
| `clear_household` | Forgets the home, the plans, and the cached reading. |

There is also a `household://profile` resource.

Air readings come from [Open-Meteo](https://open-meteo.com/). If `us_aqi` is missing, the server estimates it from the current PM2.5 with EPA breakpoints. If the network fails, it uses the last saved reading and says so.

## Run it

Python 3.12. From this folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m hearthline
```

Then open http://127.0.0.1:8080

- MCP server: http://127.0.0.1:8765/mcp
- Simulator: http://127.0.0.1:8080

The status pill should read `MCP 2025-11-25` and list 7 tools. Use the chips, the mic (Edge or Chrome), or **Play the demo**.

Demo lines, in order:

1. Remember our home in Ajmer. Riya is 8 and has asthma. I am Aditya.
2. Give me the school morning brief.
3. Should we open the windows tonight?
4. What do you remember about our home?

Refresh the page and ask the fourth line again. The home is still there. That file is `data/household.json`.

To point the simulator at an MCP server you started yourself:

```powershell
$env:HEARTHLINE_MCP_URL = "http://127.0.0.1:8765/mcp"
.\.venv\Scripts\python.exe -m hearthline.server
```

`HEARTHLINE_DATA` overrides the folder used for the household and the air cache. `HEARTHLINE_WEB_PORT` and `HEARTHLINE_MCP_PORT` change the ports.

## Tests

```powershell
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The unit tests cover the AQI scale, the plan wording, and which tools a sentence should call. They do not need the network. The live check is the demo above.

## Layout

- `hearthline/server.py` — MCP server, Streamable HTTP
- `hearthline/agent.py` — turns a sentence into tool calls
- `hearthline/bridge.py` — MCP client used by the simulator
- `hearthline/policy.py` — the household plan
- `hearthline/aqi.py` — Open-Meteo geocoding and air
- `web/` — the Alexa+ simulator
- `SUBMISSION.md` — text you can paste into the Devpost form

## License

MIT. Copyright 2026 Aditya Raj Singh.
