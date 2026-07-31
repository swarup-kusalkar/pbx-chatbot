SYSTEM_PROMPT = """You are a PBX and Contact Center support specialist at a telecom company.
You help engineers and support staff understand PBX systems, VoIP technology, IVR configuration, SIP trunks, Asterisk, and related telephony concepts.

Your rules:
1. Base your answers primarily on the knowledge base articles provided to you.
2. If the provided articles don't cover the question, say clearly:
   "I don't have detailed information on that specific topic in my knowledge base.
    For accurate guidance, consult your PBX vendor's documentation or Asterisk's
    official wiki at https://wiki.asterisk.org"
3. Never make up configuration values, CLI commands, or specifications.
4. Format responses clearly: use bullet points for lists, code blocks for any
   commands or configuration snippets.
5. Be concise and technical. Assume the user has basic telecom knowledge.
"""


def build_kb_context(chunks: list[dict]) -> list[dict]:
    if not chunks:
        return [
            {"role": "user", "content": "No relevant knowledge base articles were found for this question.\nThe user may be asking about a topic outside PBX/Contact Center technology."},
            {"role": "assistant", "content": "Understood. I don't have specific information on this topic in my knowledge base. I'll let the user know."}
        ]

    lines = ["Here are the relevant knowledge base articles for this question:\n"]
    for chunk in chunks:
        lines.append(f"--- ARTICLE: {chunk['section']} ---")
        lines.append(chunk["content"])
        lines.append("")

    kb_text = "\n".join(lines) + "\n--- END OF KNOWLEDGE BASE ---"

    return [
        {"role": "user", "content": kb_text},
        {"role": "assistant", "content": "Understood. I'll use this knowledge base to answer the user's question."}
    ]


def format_history(messages: list[dict]) -> list[dict]:
    formatted = []
    for msg in messages:
        formatted.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    return formatted


def build_prompt(
    kb_chunks: list[dict],
    history: list[dict],
    current_message: str
) -> list[dict]:
    prompt = []

    prompt.append({"role": "system", "content": SYSTEM_PROMPT})

    prompt.extend(build_kb_context(kb_chunks))

    if history:
        prompt.extend(format_history(history))

    prompt.append({"role": "user", "content": current_message})

    return prompt