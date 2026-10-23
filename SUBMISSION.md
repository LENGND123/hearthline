# Devpost paste sheet

Hackathon: Build, Ship, Shape: Amazon Developer Hackathon
https://amazonappdev2026.devpost.com/

Primary track: Alexa+
Mini challenge: Open Source
GitHub username: LENGND123
Repository: https://github.com/LENGND123/hearthline

The demo video has to be a public YouTube or Vimeo link under 3 minutes, in English, with no copyrighted music. Record the simulator while it runs. A generated clip of the idea does not show the project functioning.

## Name

Hearthline

## Tagline

An Alexa+ coach that remembers your household and turns live air quality into the school-morning or evening plan.

## Description

Hearthline is a voice coach for one home. You tell it the city and who lives there, including a child or someone with asthma. It keeps that profile after you close the page. On the next turn it checks live air quality and speaks a plan: whether outdoor PE is on, whether the classroom windows stay shut, whether pickup needs a mask, or whether tonight gets an hour of open windows and then a close-up.

The Alexa+ side is a self-hosted MCP server. It speaks Streamable HTTP and negotiates protocol 2025-11-25, which is the minimum the hackathon asks for. Tools: remember_household, get_household, check_air, plan_day, save_routine, recall_history, and clear_household. A household://profile resource exposes the saved home.

The simulator is a web app in the voice of an Alexa+ turn: you speak or type, Hearthline answers, and a card shows the AQI, the band, the people, and the next moves. The page does not touch the household file or the air API. bridge.py opens an MCP client, calls the tools, and renders what they return. The trace under the conversation lists each call so a judge can see the protocol in use.

Air data is the Open-Meteo air-quality API. No key. If the feed omits us_aqi, the server estimates it from the current PM2.5 with US EPA breakpoints and labels that estimate. If the network fails, it speaks the last saved reading and says it is saved, not live.

The plan is not a raw AQI lookup. plan_day combines the band, the focus of the question (school, evening, going outside, or right now), and who in the home is sensitive. A moderate day in Ajmer with an eight-year-old who has asthma becomes a short outdoor PE and a one-period window opening. The same reading at night becomes an hour of air and then the windows shut. An unhealthy reading cancels outdoor PE and puts a mask on the school run.

Built during the hackathon. It does not reuse the earlier School AQI Alert SMS project. That one pages a school at a fixed threshold. This one holds a household, talks over MCP, and changes the plan with the person and the time of day.

## Built with

Python, MCP Python SDK 2.3 (Streamable HTTP, protocol 2025-11-25), Starlette, Open-Meteo Air Quality API.

## Video script (under 3 minutes)

Record the browser at http://127.0.0.1:8080 with the mic muted in the OS if you would rather not capture the spoken voice, or leave it on. No music.

1. One sentence on camera or as a title card: "Hearthline is an Alexa+ coach. It remembers who lives here and decides the school run from the live air."
2. Show the status pill: MCP 2025-11-25 and 7 tools.
3. Press Play the demo. Let all four turns finish. Pause on the school card, then on the evening card, so the actions are readable.
4. Point at the MCP trace: remember_household, then plan_day.
5. Refresh the page. Ask "What do you remember about our home?" Show that Riya, Ajmer, and the last plan are still there.
6. End on the card. Say you would ask Alexa+ this on the way out the door.

## Product feedback

Tools used: the Model Context Protocol Python SDK (mcp 2.3.0) for a self-hosted Streamable HTTP server and client, spec 2025-11-25. Open-Meteo for geocoding and air quality, because the coach needs a live number and that API does not need a key. I did not use the gated Alexa+ Category SDK, MCP Toolkit, CLI, or Web Simulator. The hackathon FAQ says a self-hosted MCP server and your own web simulator are enough.

What worked: once I imported MCPServer instead of FastMCP, `run(transport="streamable-http", json_response=True, stateless_http=True)` came up on the first try. A client with `mode="legacy"` negotiated protocol 2025-11-25 and listed all seven tools. JSON responses meant I did not have to keep an SSE socket open for a local demo. The tool decorator turned plain Python functions into a schema the client could call.

What needs work: current tutorials and a lot of GitHub samples still say `from mcp.server.fastmcp import FastMCP`. On mcp 2.3.0 that import raises ModuleNotFoundError. The message does point at the v2 migration guide, but the hackathon resource page links the spec and not a Python snippet that matches the SDK a builder installs today. I also could not request AWS credits. The October 7 update says the pool is empty, so I did not put Bedrock in the loop. The decision policy is code, which is the right call for a rule a parent should be able to read, and it left the AWS Builder mini challenge out on purpose.

Onboarding: zero to a talking simulator was one evening after the import break. The protocol itself was fine. Finding which class survived the 2.0 rename was the slow part. Would I build on MCP for Alexa+ again: yes. A household that should still be there tomorrow maps cleanly onto tools plus a resource, and a judge can call the same tools without my web page.

## Open Source mini challenge

Contribution URL: https://github.com/LENGND123/hearthline
Project repository URL: https://github.com/LENGND123/hearthline
GitHub username: LENGND123

What I did: published Hearthline as a new MIT-licensed project during the hackathon. It is a Streamable HTTP MCP server and a small Alexa+ simulator for household air decisions.

How it works: the server is `python -m hearthline.server`. The simulator's agent calls it with the official MCP client. Tests cover the AQI bands and the tool choice for the demo sentences.

Why it matters: parents in cities with swinging AQI need a plan for a specific child, not a citywide number. Shipping it as a small open-source MCP server means another Alexa+ skill can call the same tools.

## Feature request

A reference Alexa+ web simulator that attaches to any local Streamable HTTP MCP server and shows the negotiated protocol version, the tool trace, and a card. Priority: important. Builders outside the gated preview were told to demo with their own front end. A 200-line reference page on the resource list would have made the "is this MCP enough?" question obvious, and it would give every submission the same card surface to design against.

## Friction log

1. Task: install the Python MCP SDK and start a Streamable HTTP server on spec 2025-11-25.
   Steps: created a Python 3.12 venv, installed mcp 2.3.0, and tried the FastMCP setup used in current write-ups.
   Expected: `from mcp.server.fastmcp import FastMCP` and `mcp.run(transport="streamable-http")`.
   Actual: importing mcp.server.fastmcp raises ModuleNotFoundError. The module body says FastMCP was renamed to MCPServer in mcp 2.x.
   Severity: important.
   Workaround: `from mcp.server import MCPServer`, then run Streamable HTTP with json_response and stateless_http. The simulator client uses mode="legacy" so the handshake stays on 2025-11-25.
   Suggestion: add one Python block to the Alexa+ resource page that matches mcp 2.x, and say the protocol pin the hackathon will accept.

2. Task: use AWS in the agent so the project could also enter the AWS Builder mini challenge.
   Steps: read the hackathon rules and the October 7 credit update, then looked for a no-credit Bedrock path.
   Expected: promotional credits were offered earlier in the event for Bedrock or AgentCore.
   Actual: the credit form closed on October 7 because the codes ran out. I was not going to put a paid model call in a demo I cannot afford to leave running for judges.
   Severity: nice-to-have for Hearthline, important for the mini challenge.
   Workaround: the plan is a readable policy in policy.py, and the live number comes from Open-Meteo. I did not enter AWS Builder.
   Suggestion: a local, no-account sample for the mini challenge, or a few credits reopened in the last week of submissions.
