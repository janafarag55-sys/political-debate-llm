"""
Government vs Opposition: a political debate between two LLMs.

- One model plays the government; another plays the opposition.
- Models are accessed through Groq.
- The UI is built with Gradio.
- The debate is capped at 10 rounds (one round = two speeches).
"""

import os

import gradio as gr
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MAX_ROUNDS = 10
GOV_MODEL = os.getenv("GOV_MODEL", "openai/gpt-oss-120b")
OPP_MODEL = os.getenv("OPP_MODEL", "openai/gpt-oss-20b")

RULES = """
RULES YOU MUST FOLLOW:
1. Support every argument with real, verifiable data: figures, statistics, years and
   the source (e.g. World Bank, IMF, UN, national statistics office, OECD).
2. Never invent numbers. If you are not sure of an exact figure, say "approximately"
   or use a figure you are confident about. Do not make up sources.
3. Answer the other side's last point directly, then add one new argument.
4. Keep each reply under 150 words. Be professional and respectful, no insults.
5. Speak only as your role. Do not write the other side's lines.
6. Never concede the debate or adopt the other side's proposals. Defend your own
   position firmly, and only acknowledge a point briefly before rebutting it.
"""


def system_prompt(role: str, country: str, topic: str) -> str:
    focus = f" Focus especially on: {topic}." if topic.strip() else ""
    if role == "government":
        identity = (
            f"You are a spokesperson for the GOVERNMENT of {country}. "
            "Defend its policies and explain achievements and plans, without denying "
            "well-established facts."
        )
    else:
        identity = (
            f"You are a spokesperson for the OPPOSITION in {country}. "
            "Critique government policy using evidence and propose alternatives."
        )
    return f"{identity}{focus}\nYou are in a live political debate.\n{RULES}"


def ask_llm(client: Groq, model: str, system: str,
            transcript: list[tuple[str, str]], role: str) -> str:
    messages = [{"role": "system", "content": system}]
    for speaker, content in transcript:
        messages.append({
            "role": "assistant" if speaker == role else "user",
            "content": content,
        })

    if not transcript:
        messages.append({
            "role": "user",
            "content": "Give your opening statement. State the main argument and support it with evidence.",
        })

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.5,
        max_tokens=1500,
    )
    answer = response.choices[0].message.content
    return (answer or "").strip()


def run_debate(country: str, topic: str, rounds: int):
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or api_key == "paste_your_real_key_here":
        raise gr.Error(
            "GROQ_API_KEY is missing. Add your key to the local .env file, then restart the app."
        )
    if not country or not country.strip():
        raise gr.Error("Please enter a country name.")

    country = country.strip()
    topic = (topic or "").strip()
    rounds = max(1, min(int(rounds), MAX_ROUNDS))
    client = Groq(api_key=api_key)

    gov_system = system_prompt("government", country, topic)
    opp_system = system_prompt("opposition", country, topic)
    transcript: list[tuple[str, str]] = []
    chat: list[dict[str, str]] = []

    for round_number in range(1, rounds + 1):
        for role, model, system in (
            ("government", GOV_MODEL, gov_system),
            ("opposition", OPP_MODEL, opp_system),
        ):
            try:
                answer = ask_llm(client, model, system, transcript, role)
            except Exception as exc:
                # Do not expose the API key in the UI; provider errors are shown for troubleshooting.
                message = str(exc).replace(api_key, "[REDACTED]")
                raise gr.Error(
                    f"Groq request failed: {message}\n"
                    "Check your internet connection, model availability, API key, and free-tier limits."
                ) from None

            transcript.append((role, answer))
            label = "🏛️ Government" if role == "government" else "🗳️ Opposition"
            chat.append({
                "role": "assistant" if role == "government" else "user",
                "content": f"**{label} — Round {round_number}/{rounds}**\n\n{answer}",
            })
            yield chat


with gr.Blocks(title="Government vs Opposition Debate") as demo:
    gr.Markdown(
        "# 🏛️ Government vs 🗳️ Opposition\n"
        "Two LLMs debate political issues in the country you choose. "
        f"The maximum is {MAX_ROUNDS} rounds.\n\n"
        "**Important:** Model responses can contain mistakes. Verify statistics and sources independently."
    )
    with gr.Row():
        country = gr.Textbox(label="Country", placeholder="e.g. Egypt", scale=2,lines=1,max_lines=1)
        topic = gr.Textbox(
            label="Topic (optional)",
            placeholder="e.g. economy, education, healthcare",
            scale=2,
            lines=1,
            max_lines=1,
        )
        rounds = gr.Slider(1, MAX_ROUNDS, value=3, step=1, label="Rounds", scale=1)

    start = gr.Button("Start debate", variant="primary")
    chatbot = gr.Chatbot(label="Debate", height=550, type="messages")
    start.click(run_debate, inputs=[country, topic, rounds], outputs=chatbot)

if __name__ == "__main__":
    demo.queue().launch()
