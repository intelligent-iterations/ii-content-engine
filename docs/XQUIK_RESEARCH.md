# Xquik Research Imports

Use reviewed Xquik exports as saved research context before generating
carousels, videos, captions, or scheduled X posts.

The importer is local only. It reads JSON or JSONL files, normalizes common
tweet fields, validates tweet IDs and X URLs, and writes a research artifact
under `research/` by default. That keeps the project's template-first workflow:
agents use saved repo state as context instead of one-off prompt text.

## Usage

```bash
node code/cli/xquik-research.js xquik-export.jsonl
```

Optional flags:

```bash
node code/cli/xquik-research.js xquik-export.jsonl --output research/launch.json --topic "Launch research" --limit 25
```

The command accepts:

- a JSON array of tweet rows
- JSONL with one tweet row per line
- objects wrapping rows in `tweets`, `posts`, `data`, `results`, or `items`

## Output

The output file includes:

- `summary` notes for the agent
- `sources` with source X URLs and timestamps
- normalized `posts` with author, text, URL, and engagement metrics

Review the artifact before using source text in a caption or post. Verify the
content is relevant, lawful to use, and consistent with the account voice.
