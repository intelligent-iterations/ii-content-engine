# BRANCH POLICY — READ FIRST

**This repository MUST always be checked out on the `dev` branch. No exceptions.**

- Never switch this working copy to `main`, a feature branch, or detached HEAD. All work happens on `dev`.
- If `git submodule update`, a merge, or any tool moves something off `dev`, switch it back to `dev` immediately before continuing.

---

# CLAUDE.md

## Repo Role

This repo is template-first. Treat user ideas as reusable formats whenever possible, not disposable prompt requests.

Keep separate:
1. `template`
2. `research artifact`
3. `render settings`

Anything that matters for reruns must be saved in repo state.

## Research

All research artifacts go under `research/`. This directory is gitignored — research is local working state, not committed to the repo. Use it for format research, prompt strategy notes, practitioner findings, and any intermediate research files. Reference research from templates and run artifacts, but keep the raw research in `research/`.

If the user provides substantial research directly in chat, such as a long pasted guide, strategy memo, or prompt reference they want used, treat that as valid research input. Distill it into saved repo state and rely on it by default instead of doing redundant external research that could overwrite or dilute the user's supplied direction. Only do additional research if the user asks for it or if there is a clear gap that blocks execution.

## Output Rules

- Video runs go under `output/videos/<concept-slug>/`
- Carousel runs go under `output/carousels/<concept-slug>/`
- Post-ready assets go under `output/scheduled_videos/` or `output/scheduled_carousels/`

For video runs, save:
- `<slug>.md`
- `research.json`
- `<slug>_caption.txt`
- `asset-manifest.json`
- `plans/tool-plan.json`
- `plans/execution-plan.json`
- `clips/`
- `<slug>.mp4`

Do not scatter video artifacts across the repo root, `downloads/`, or ad hoc folders. A video run is complete only when its working files and final outputs live together inside that run's own folder.

## Required Rule Files

Read and follow the matching rule file before doing substantial work:

- Video template work:
  - `.claude/rules/video-template-first.md`
  - `.codex/rules/video-template-first.md`
- Grok image/video prompting:
  - `.claude/rules/grok-video-prompting.md`
  - `.codex/rules/grok-video-prompting.md`
- Carousel work:
  - `.claude/rules/carousel-template-first.md`
  - `.codex/rules/carousel-template-first.md`
- Prompt best practices:
  - `docs/prompts/STORY_CHARACTER_PROMPT_GUIDE.md`

## Guidance Folders

Treat this folder as the source of truth for reusable documentation guidance:

- `docs/prompts/` for prompt-authoring guidance, asset-chain rules, and prompt best practices

Before authoring prompts, assets, or render jobs:

1. Check `docs/prompts/` for matching prompt guidance.
2. If the task is a continuity-sensitive character story, follow the workflow chain:
   `hero portrait -> derived character sheet -> scene start frames -> video`
3. For continuity-sensitive character stories, run the asset executor path before rendering clips.
4. For continuity-sensitive character stories, scene start frames should default to the approved ordered reference sheets for the visible characters. Do not auto-expand scene references back into sibling hero portraits unless the template explicitly needs that.

## Default Behavior

- New or materially changed formats require research first.
- If the request matches a saved prompt-best-practices guide, read the relevant file under `docs/prompts/` and apply it before authoring prompts, character assets, or story beats.
- Substantial user-supplied research can satisfy the research requirement for a format change if it is specific enough to drive the template or run artifact.
- For new or materially changed prompting work, do narrow research first, then wide research.
- Narrow research means starting with the exact format, character type, visual style, or failure mode involved in the request.
- Narrow research should begin with likely creator language at the right level of abstraction, not generic umbrella labels and not hyper-specific one-off phrasing. Search terms should usually be broad, highly relevant, and around 4 words or fewer.
- If the first narrow pass is weak, reformulate and retry several times with adjacent niche phrasings, platform-native slang, and likely creator wording before treating the niche as under-documented.
- Do not stop after one weak search round when the format is plausibly something creators have already tested. Try multiple query shapes across X, Reddit, search engines, and adjacent practitioner communities first.
- Do at least 5 distinct web research searches or passes before moving on from research into prompt writing for a new or materially changed format.
- Wide research means expanding into broader model behavior, continuity tactics, reference-image reuse patterns, and adjacent prompt strategies.
- For prompting quality research, prioritize recent practitioner advice on X and Reddit over official docs. Use official docs mainly for capability limits, API behavior, and product mechanics.
- The agent is the primary brain for planning, scripting, template design, prompt contracts, and saved run artifacts. The agent must author the compilation markdown locally and save it before any render step starts.
- Do not use Grok chat to author, repair, or rewrite the core shot plan, compilation markdown, reusable template, or caption strategy.
- Use Grok text/chat only as a research input when needed, such as checking recent practitioner advice from X or collecting external prompt opinions that are then rewritten and distilled locally by the agent into repo state.
- The important boundary is this:
  - Codex/Claude should author the template and filled run artifacts.
  - The repo should then render and queue the output.
- The video CLI/render pipeline should consume an existing local `<slug>.md` artifact. Treat markdown generation as agent work, not a Grok runtime step.
- Executors should consume saved JSON plans under `output/videos/<slug>/plans/`, not ad hoc inline prompt assembly.
- Post captions in `<slug>_caption.txt` should be authored locally by the agent/local caption writer from saved repo state, not by Grok.
- On-video dialogue captions should come from the rendered clip audio/transcription pipeline, with prompt dialogue used only as fallback alignment data.
- Prefer adding or adapting templates over hard-coded prompt branches.
- If `XAI_API_KEY` is missing, keep the run template-driven and render from saved artifacts.
- If `XAI_API_KEY` is missing but a saved Grok web session exists, try the browser automation path from the saved artifacts rather than stopping at markdown/research generation.
- Before treating a video render as blocked, check for browser-session fallback files such as `auth/grok-session-cookies.json`, `auth/grok-storage-state.json`, or `cookies/x_cookies.json`.
- Browser fallback is only valid if the Grok submit path starts a real generation job. If browser submit opens the `SuperGrok` subscribe modal instead, treat the run as browser-blocked and do not scrape Discover/gallery media as a fake result.
- Caption nudge: carousel captions and reel/video captions should usually land between 2100 and 2200 characters, front-load the hook in the first 125 characters, stay SEO-friendly, and use the local caption-writing fallback instead of treating missing `XAI_API_KEY` as a caption blocker.
- Posted-video default: queued videos should stay raw in `scheduled_videos/` under `II_ROOT`, the standard promo clip from `II_ROOT/assets/plug.mov` should be appended immediately before each platform post attempt, and the caption opener should be `Make videos like this by searching ii-content-engine on GitHub.`
- For stitched multi-clip videos, treat continuity as a first-order requirement: the script, acting beats, character design, wardrobe, environment, and cinematic style should survive across clips unless the format explicitly calls for change.
- If continuity matters across clips, prefer image-conditioned generation and reference-image reuse whenever the toolchain supports it. Do not let each clip reinvent the same character, environment, object, or world style from scratch if that can be avoided.
- For continuity-sensitive character stories, the required default asset chain is:
  `hero portrait -> derived character sheet -> scene start frames -> video`
- For continuity-sensitive character stories, the scene-start-frame stage should normally use the ordered approved character sheets as its reference inputs.
- For continuity-sensitive character stories, scene-start-frame assets should be saved at the target render aspect ratio, normally portrait `9:16`, rather than left as landscape references.
- For continuity-sensitive character stories, do not jump straight from markdown to video render if the required asset chain has not been generated from saved repo state.
- The video system supports both `per_clip` image-to-video references and `shared_reference` reuse across clips. Use `per_clip` for isolated beats or loose compilations; use `shared_reference` whenever a stitched sequence depends on continuity of characters, environments, objects, or overall world style.
- If native dialogue harms acting quality, reduce dialogue complexity and let visuals or captions carry more of the story.
- Voice-line best practice for multi-character clips: default to one named speaker per clip, explicitly mark `Speaker:`, `Silent characters:`, `Dialogue:`, `Action:`, and `Direction:` in the saved markdown, keep spoken lines short and literal, and do not let silent on-screen characters share or mouth the line.
- Do not render first-pass videos for unfamiliar or continuity-sensitive formats until the research has been distilled into saved repo state.
- Preserve reusable knowledge in repo files, not in chat.

## Key Files

- Video templates: `prompts/video-templates.json`
- Video template builder: `code/video/template-registry.js`
- Video generator: `code/video/generate-video.js`
- Video pipeline: `code/video/generate-video-compilation.js`
- Carousel templates: `prompts/carousel-templates.json`

## Grok Auth Flow

If `XAI_API_KEY` is not set and no valid session exists at `auth/grok-storage-state.json`, the agent needs browser cookies to use Grok.
If `cookies/x_cookies.json` exists, the browser path can bootstrap a fresh `auth/grok-storage-state.json` by completing the xAI `Login with 𝕏` flow in Playwright.
Even with saved cookies, browser generation is not valid unless submit reaches a real Grok generation job rather than the `SuperGrok` subscribe modal.

Before starting auth, the user should tell the agent which platform(s) they are already signed into and which Chrome profile email each one uses.

On macOS, Chrome cookie extraction may fail unless the login keychain is unlocked first. If cookie decryption errors appear or `security` reports that user interaction is not allowed, unlock `~/Library/Keychains/login.keychain-db` before retrying.

To authenticate:

1. Ask the user to confirm they are logged into [grok.com](https://grok.com) in one of their Chrome profiles.
2. Ask which Chrome profile (email) they are logged in with.
3. Run the export script with that profile:
   ```bash
   npm run auth:grok -- --profile "Profile 3"
   ```
   The user will need to approve the macOS Keychain prompt to decrypt Chrome cookies.
4. Verify the output shows auth cookies (sso, auth_token, ct0, etc.).

The exported cookies are saved to `auth/grok-storage-state.json` and gitignored. No secrets are committed.

If the user does not know their profile directory name, run without `--profile` to show a numbered list of all Chrome profiles with their email addresses.

## Posting Auth Flow

The same Chrome cookie extraction approach works for Instagram, TikTok, and X posting cookies. The user must be logged into the relevant platform in a Chrome profile.

Before extracting cookies, ask the user which of Instagram, TikTok, and X they are already signed into and which Chrome profile email each platform uses.

On macOS, onboarding the posting cookies may require unlocking the login keychain first so Chrome cookies can be decrypted. If extraction fails with a browser-cookie decryption error or keychain access error, unlock `~/Library/Keychains/login.keychain-db` and retry.

To extract posting cookies, run `browser-cookie3` for the target domain and save to the expected cookie file:

- **Instagram** → `cookies/instagram_cookies.json` (domain: `.instagram.com`)
- **TikTok** → `cookies/tiktok_cookies.json` (domain: `.tiktok.com`)
- **X** → `cookies/x_cookies.json` (domain: `.x.com`)

The user may use different Chrome profiles for different platforms (e.g. one account for Instagram, another for TikTok). Always ask which Chrome profile to use for each platform.

Cookie files are a JSON array of objects with fields: `name`, `value`, `domain`, `path`, `expires`, `httpOnly`, `secure`, `sameSite`.

All cookie files are gitignored. No secrets are committed.

The posting scripts detect usernames at runtime by logging in with cookies and reading the username from the platform page (e.g. TikTok Studio HTML, Instagram nav, X profile). No username env vars are required. The following env vars are optional hints — if set, they're used as a starting point, but the scripts always verify from the platform:

- `INSTAGRAM_USERNAME` — optional, detected from logged-in page
- `TIKTOK_ACCOUNT_NAME` — optional, detected from TikTok Studio
- `X_USERNAME` — optional, detected from X profile

## Social Media Accounts — Source of Truth

Never hardcode, guess, or assume usernames. The posting scripts derive them at runtime by logging in with stored cookies and reading the username from the platform's own page or API data. If a username is needed to construct a permalink or URL, fetch it from the platform first.

## Standard

The work is not done if the output succeeded once but the reusable template/research state was not saved.
