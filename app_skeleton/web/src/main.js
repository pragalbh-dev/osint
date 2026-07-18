import "./style.css";

const app = document.querySelector("#app");
app.innerHTML = `
  <main class="wrap">
    <div class="badge">SESSION X0 · WALKING SKELETON</div>
    <h1>Chanakya OSINT</h1>
    <p class="sub">Auditable OSINT analysis &amp; monitoring — deploy pipeline online.</p>
    <p class="tag">It boots. Node build → static bundle → FastAPI, served same-origin.</p>
    <div class="health" id="health">/health → checking…</div>
    <footer>image → GHCR → docker&nbsp;compose on EC2 → Cloudflare&nbsp;Tunnel</footer>
  </main>
`;

// Prove the API from the page itself: relative "./health" resolves to /health.
const el = document.querySelector("#health");
fetch("./health", { cache: "no-store" })
  .then((r) => r.json().then((j) => ({ ok: r.ok, j })))
  .then(({ ok, j }) => {
    el.textContent = `/health → ${j.status ?? "?"}  (${ok ? "200" : "error"})`;
    el.classList.add(ok ? "ok" : "err");
  })
  .catch(() => {
    el.textContent = "/health → unreachable";
    el.classList.add("err");
  });
