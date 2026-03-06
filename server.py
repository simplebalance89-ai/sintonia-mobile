"""Sinton.ia Mobile — Lightweight chat PWA for Peter's phone."""
import os
import httpx
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI()

AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://pwgcerp-9302-resource.openai.azure.com/")
AZURE_KEY = os.getenv("AZURE_OPENAI_KEY", "")
AZURE_MODEL = os.getenv("AZURE_OPENAI_MODEL", "gpt-4.1-mini")
PIN = os.getenv("APP_PIN", "1234")

SYSTEM_PROMPT = """You are Sinton.ia Mobile — a quick-access version of Peter's AI partner.

You are NOT the full Sinton.ia (that runs on Claude Code on the ThinkStation). You are the phone version — fast, concise, research-ready.

Your job:
- Quick research and answers
- Hash out ideas with Peter
- Help him think through problems
- Give him data he can act on

Style:
- Direct. No fluff. No corporate speak.
- Short paragraphs. Peter reads this on his phone.
- If he asks about work (C365, EnPro, Luxor, Candy, Hosa) — give practical answers.
- If he asks about personal projects (Edge Crew, Casa Cuervo, Casa Companion, Simple Balance Music) — same.
- If something needs full Sinton.ia attention, say "Ship this to the desk" so he knows to export it.

Peter is a Principal Solutions Architect, AI & Automation. He knows his stuff. Don't over-explain.

Current date: {date}
"""


@app.post("/api/auth")
async def auth(request: Request):
    body = await request.json()
    if body.get("pin") == PIN:
        return {"ok": True}
    raise HTTPException(status_code=401, detail="Wrong PIN")


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    if body.get("pin", "") != PIN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    messages = body.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="No messages")

    system = SYSTEM_PROMPT.format(date=datetime.now().strftime("%B %d, %Y"))
    azure_messages = [{"role": "system", "content": system}] + [
        {"role": m["role"], "content": m["content"]} for m in messages
    ]
    url = f"{AZURE_ENDPOINT.rstrip('/')}/openai/deployments/{AZURE_MODEL}/chat/completions?api-version=2024-12-01-preview"

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, headers={"api-key": AZURE_KEY, "Content-Type": "application/json"},
                              json={"messages": azure_messages, "max_tokens": 2000, "temperature": 0.7})
    if r.status_code != 200:
        return JSONResponse({"error": f"Azure {r.status_code}: {r.text}"}, status_code=502)
    return {"reply": r.json()["choices"][0]["message"]["content"]}


@app.post("/api/export")
async def export(request: Request):
    body = await request.json()
    if body.get("pin", "") != PIN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    messages = body.get("messages", [])
    title = body.get("title", "Sinton.ia Mobile Export")
    tag = body.get("tag", "sinton.ia")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"# {title}", f"**From:** Sinton.ia Mobile", f"**Date:** {now}", f"**Tag:** [{tag}]", "", "---", ""]
    for m in messages:
        role = "Peter" if m["role"] == "user" else "Sinton.ia"
        lines.append(f"**{role}:** {m['content']}")
        lines.append("")
    lines.extend(["---", "*Exported from Sinton.ia Mobile*"])
    return {"markdown": "\n".join(lines), "filename": f"MOBILE_EXPORT_{now.replace(':', '').replace(' ', '_')}.md"}


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "sintonia-mobile", "time": datetime.now().isoformat()}

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def index():
    return FileResponse("static/index.html")

@app.get("/manifest.json")
async def manifest():
    return FileResponse("static/manifest.json")

@app.get("/sw.js")
async def sw():
    return FileResponse("static/sw.js", media_type="application/javascript")
