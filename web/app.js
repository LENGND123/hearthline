const log = document.querySelector("#log");
const trace = document.querySelector("#trace");
const card = document.querySelector("#card");
const status = document.querySelector("#status");
const form = document.querySelector("#composer");
const input = document.querySelector("#say");
const mic = document.querySelector("#mic");
const demo = document.querySelector("#demo");

const DEMO = [
  "Remember our home in Ajmer. Riya is 8 and has asthma. I am Aditya.",
  "Give me the school morning brief.",
  "Should we open the windows tonight?",
  "What do you remember about our home?",
];

let speaking = window.speechSynthesis || null;
let busy = false;

function bandClass(band) {
  const key = String(band || "").toLowerCase();
  if (key.includes("hazard")) return "hazard";
  if (key.includes("very")) return "very";
  if (key.includes("sensitive")) return "sensitive";
  if (key.includes("unhealthy")) return "unhealthy";
  if (key.includes("moderate")) return "moderate";
  if (key.includes("good")) return "good";
  return "unknown";
}

function addBubble(kind, text) {
  const item = document.createElement("div");
  item.className = `bubble ${kind}`;
  const who = document.createElement("span");
  who.className = "who";
  who.textContent = kind === "user" ? "You" : "Hearthline";
  item.append(who, document.createTextNode(text));
  log.append(item);
  log.scrollTop = log.scrollHeight;
}

function showTrace(steps, protocol) {
  if (!steps || !steps.length) {
    trace.hidden = true;
    return;
  }
  trace.hidden = false;
  const lines = steps.map((step) => {
    const args = Object.entries(step.arguments || {})
      .filter(([, value]) => value !== "" && value !== 0 && value != null)
      .map(([key, value]) => `${key}=${value}`)
      .join(", ");
    return `<div><strong>${step.tool}</strong>${args ? `(${args})` : "()"} → ${step.preview}</div>`;
  });
  trace.innerHTML = `<div>MCP ${protocol || ""} · Streamable HTTP</div>${lines.join("")}`;
}

function showCard(payload) {
  if (!payload || (payload.aqi == null && !(payload.people || []).length && !payload.headline)) {
    return;
  }
  const people = (payload.people || [])
    .map((person) => {
      const note = person.note ? ` · ${person.note}` : "";
      return `<li>${person.name} · ${person.role}${note}</li>`;
    })
    .join("");
  const actions = (payload.actions || [])
    .map((action, index) => {
      return `<li><span>${index + 1}</span><div><strong>${action.label}</strong><p>${action.detail}</p></div></li>`;
    })
    .join("");
  const aqi = payload.aqi == null ? "–" : payload.aqi;
  const cached = payload.cached ? "Saved reading, not live." : "Live reading.";
  card.className = "card";
  card.innerHTML = `
    <div class="card-top">
      <div>
        <p class="card-kicker">${payload.title || "Hearthline"}</p>
        <h2 class="place">${payload.place_label || payload.city || "This home"}</h2>
      </div>
      <div class="aqi">
        <b>${aqi}</b>
        <span class="aqi-label">US AQI</span>
      </div>
    </div>
    <span class="band ${bandClass(payload.band)}">${payload.band || "Not checked yet"}</span>
    <h3 class="headline">${payload.headline || ""}</h3>
    ${people ? `<ul class="people">${people}</ul>` : ""}
    ${actions ? `<ol class="actions">${actions}</ol>` : ""}
    <p class="note">${cached}${payload.pm2_5 != null ? ` PM2.5 ${payload.pm2_5}.` : ""} ${payload.source ? `Source: ${payload.source}.` : ""}</p>
  `;
}

function speak(text) {
  if (!speaking) return;
  speaking.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  utterance.rate = 1;
  speaking.speak(utterance);
}

async function ask(text, options = {}) {
  const trimmed = text.trim();
  if (!trimmed || busy) return;
  busy = true;
  addBubble("user", trimmed);
  input.value = "";
  try {
    const response = await fetch("/api/say", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: trimmed }),
    });
    const body = await response.json();
    if (!response.ok) {
      addBubble("alexa", body.error || "Something went wrong.");
      return;
    }
    addBubble("alexa", body.speech);
    showTrace(body.trace, body.protocol);
    showCard(body.card);
    if (!options.silent) speak(body.speech);
  } catch (error) {
    addBubble("alexa", "I couldn't reach the simulator. Is Hearthline still running?");
  } finally {
    busy = false;
  }
}

async function refreshStatus() {
  try {
    const response = await fetch("/api/health");
    const body = await response.json();
    if (!response.ok) throw new Error(body.error || "down");
    status.className = "status ok";
    status.textContent = `MCP ${body.protocol} · ${body.tools.length} tools`;
  } catch (error) {
    status.className = "status bad";
    status.textContent = "MCP server is not answering";
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  ask(input.value);
});

document.querySelectorAll("[data-say]").forEach((button) => {
  button.addEventListener("click", () => ask(button.dataset.say));
});

demo.addEventListener("click", async () => {
  for (const line of DEMO) {
    await ask(line, { silent: false });
    await new Promise((resolve) => setTimeout(resolve, 400));
  }
});

const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (!Recognition) {
  mic.disabled = true;
  mic.textContent = "Type";
} else {
  const recognition = new Recognition();
  recognition.lang = "en-US";
  recognition.interimResults = false;
  recognition.onstart = () => mic.classList.add("listening");
  recognition.onend = () => mic.classList.remove("listening");
  recognition.onresult = (event) => {
    const said = event.results[0][0].transcript;
    input.value = said;
    ask(said);
  };
  mic.addEventListener("click", () => recognition.start());
}

addBubble("alexa", "Tell me the city and who lives there. Then ask for the school morning brief.");
refreshStatus();
