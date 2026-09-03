import json
import anthropic
from app.config import settings

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
MODEL = "claude-sonnet-4-6"
BATCH_SIZE = 20


def classify_entries(lines: list[str]) -> list[dict]:
    """
    Classify each log line as normal, suspicious, or critical.

    Processes lines in batches of BATCH_SIZE to reduce API calls.
    Returns a list of dicts with keys: line_number, classification, reason.
    """
    results: list[dict] = []

    for batch_start in range(0, len(lines), BATCH_SIZE):
        batch = lines[batch_start : batch_start + BATCH_SIZE]

        numbered_lines = "\n".join(
            f"{batch_start + i + 1}: {line}" for i, line in enumerate(batch)
        )

        message = _client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=(
                "You are a security analyst. Classify each log line as: normal, suspicious, or critical. "
                "Return ONLY valid JSON array: "
                '[{"line": <number>, "classification": "normal|suspicious|critical", "reason": "<one sentence>"}]. '
                "Be concise."
            ),
            messages=[
                {
                    "role": "user",
                    "content": f"Classify these log lines:\n\n{numbered_lines}",
                }
            ],
        )

        response_text = message.content[0].text.strip()

        # Strip markdown code fences if present
        if response_text.startswith("```"):
            lines_resp = response_text.splitlines()
            response_text = "\n".join(
                line for line in lines_resp
                if not line.startswith("```")
            ).strip()

        parsed: list[dict] = json.loads(response_text)

        for item in parsed:
            results.append(
                {
                    "line_number": item["line"],
                    "classification": item["classification"].lower(),
                    "reason": item["reason"],
                }
            )

    return results


def generate_summary(
    filename: str,
    normal: int,
    suspicious: int,
    critical: int,
    critical_entries: list[str],
) -> str:
    """
    Generate a 2-3 paragraph incident summary based on analysis counts and critical lines.
    """
    sample_lines = "\n".join(f"- {entry}" for entry in critical_entries[:5])

    prompt = (
        f"You analyzed the log file '{filename}' and found:\n"
        f"- Normal entries: {normal}\n"
        f"- Suspicious entries: {suspicious}\n"
        f"- Critical entries: {critical}\n\n"
        f"Sample critical log lines:\n{sample_lines}\n\n"
        "Write a 2-3 paragraph incident summary for a security team. "
        "Cover: what the logs suggest is happening, the severity level, "
        "and recommended immediate actions. Be direct and actionable."
    )

    message = _client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text.strip()
