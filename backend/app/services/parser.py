MAX_LINES = 500


def parse_log_file(content: str) -> list[str]:
    """Split log content into non-empty lines, capped at MAX_LINES to control costs."""
    lines = content.splitlines()
    non_empty = [line for line in lines if line.strip()]
    return non_empty[:MAX_LINES]
