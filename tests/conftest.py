import json
import subprocess
import sys


def run_crawler(crawler_name, parents_data=None, season=2024, tmp_path=None):
    """Run a crawler as a subprocess and return parsed JSONL items.

    This runs each crawler in its own process, matching real CLI usage
    and avoiding Crawlee event-loop isolation issues between tests.
    """
    cmd = [sys.executable, "-m", "tfmkt", crawler_name, "-s", str(season)]

    if parents_data is not None and tmp_path is not None:
        parents_file = tmp_path / "parents.json"
        lines = []
        if isinstance(parents_data, list):
            for item in parents_data:
                lines.append(json.dumps(item))
        else:
            lines.append(json.dumps(parents_data))
        parents_file.write_text("\n".join(lines) + "\n")
        cmd.extend(["-p", str(parents_file)])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    assert result.returncode == 0, f"Crawler failed:\n{result.stderr}"

    items = []
    for line in result.stdout.strip().splitlines():
        if line:
            items.append(json.loads(line))
    return items
