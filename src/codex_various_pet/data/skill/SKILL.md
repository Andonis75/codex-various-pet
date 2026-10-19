---
name: various-pet
description: Make a local Codex desktop v1 pet from a character image by actively operating signed-in ChatGPT web, generating and downloading animation strips, reviewing motion, and installing the accepted result. Use for Codex desktop pets; not ChatGPT Work cloud Pets.
---

# Various Pet

Take the user's reference and desired changes through the full desktop-pet workflow. **Do the browser work and local processing yourself**, rather than handing the user commands or asking “continue” after each state. Preserve character identity, the chosen website and existing authorization. Deliver real source strips, a checked v1 atlas, an actual visual motion review, review record and installed files when requested. Keep the primary user experience in the original ChatGPT page and the resulting Codex pet; do not require the user to operate an extra preview website.

The target is Codex desktop v1, checked against `26.1013`, not ChatGPT Work cloud Pets. Do not claim every Codex environment has browser control.

## Prepare the execution route

Read [browser-playbook.md](references/browser-playbook.md) for the concrete browser loop and [web-generation.md](references/web-generation.md) for identity and row prompts. Read [format.md](references/format.md) before assembly/install.

When starting from the repository URL, clone or reuse the checkout, read its `README.md` and `AGENTS.md`, then run its `tools/bootstrap.py` internally with an available Python 3.10+ interpreter. The script creates the repository's `.venv` and returns JSON with `python`, `repo` and `version`. Use the returned Python path to invoke `-m codex_various_pet`; the user does not need to install the skill first. Preserve original bootstrap errors if it fails.

When this skill was installed separately, resolve this `SKILL.md` directory and use its bundled `scripts/run.py` with the available Python interpreter. Do not assume a global executable is on PATH. In the commands below replace `<runner>` with the actual route: either the bootstrap Python plus `-m codex_various_pet`, or Python plus the installed skill's absolute `scripts/run.py` path. These are agent-internal operations, not commands for the user to type one by one.

```text
<runner> init ./my-pet --reference ./reference.png --name "Pet name"
<runner> prompts ./my-pet
```

Use a dedicated directory. Resume existing work instead of overwriting accepted sources. Edit `identity.md` for this character, then regenerate `prompts.md`. Obtain the attachment's real local file through available file/attachment tools before using it; never invent a path.

Discover browser tools from the current catalog and read their actual documentation. Reuse the user's intended signed-in tab. Tool signatures, state IDs, uploads and downloads come from this environment. If no controller exists, report that concrete limitation and use the manual fallback below.

## Execute generation

1. **Upload and lock identity.** Upload the actual reference in the intended ChatGPT web conversation. Submit the identity and requested style, preserving asymmetric clothing/accessories. Establish one canonical image; ask only if essential identity information is genuinely missing.
2. **Prove one full row.** Generate idle first. Wait for the real generation, download its original through an observed supported control, save `source/idle-strip.png`, decode it and inspect alpha and identity. A screenshot, painted checkerboard or invented URL is not a valid source.
3. **Complete remaining states.** Generate one row at a time with the same reference. Save each real original under its required name. Inspect count, spacing, clipping and identity after each row. A symmetric character may use a recorded horizontal mirror of an actually reviewed right-run; otherwise generate left-run independently. Never reverse temporal order to simulate a direction.
4. **Repair bounded defects.** Use the actual inspection image/error to request a correction to only that row. Retain the previous original, download the revision and inspect again. Continue ordinary retries without waiting for “continue.” Pause only when login/human verification, quota or a persistent defect blocks progress; retain accepted rows and explain the exact required action. Do not loop indefinitely or switch to an unrequested API.

Never erase all white pixels to simulate transparency or count holds/mirrors as independent generations. Use the bundled pipeline for measured extraction/assembly, not a hand-drawn placeholder or self-written success report.

## Build and visually review real motion internally

```text
<runner> inspect ./my-pet
<runner> build ./my-pet
```

Review the real contact sheets, GIFs and ordered frame images yourself using available image/animation tools. Inspect every state and its timing, not only one still frame. Check identity and head size, foot registration, true gait, jump ascent/descent, clean edges and idle transitions. If a viewer exposes only a GIF's first frame, inspect the decoded ordered frames and durations rather than claiming it played.

Interactive HTML is optional: run `<runner> preview ./my-pet` only when it helps internal QA, open it with a supported browser surface, and use playback/step/scale/background controls as needed. If a loopback service is needed, restrict it to this work directory. After QA, close only the temporary preview tab and stop only the service you created; preserve the user's ChatGPT tab. Do not hand the user an extra page as a required next step.

Geometry/alpha/hash checks do not establish motion quality. Correct visually failed rows and repeat inspection, build and real visual review. Writing HTML does not prove it was viewed. See [troubleshooting.md](references/troubleshooting.md) for recovery.

## Review and install when already authorized

After actually examining and accepting the current motion and frames, record that review. If the user asked for installation, proceed without another redundant permission question:

```text
<runner> approve ./my-pet
<runner> install ./my-pet --slug my-pet
```

`approve` is non-interactive and asserts the operator already inspected this exact build. Never invoke it merely to clear a gate. Installation requires matching hashes, geometry and review. Preserve existing pets; use an unused slug for a new revision instead of overwriting. Respect `CODEX_HOME` and the actual destination.

Verify installed files. Inspect desktop selection if a supported tool exists; otherwise give the one remaining selection step. State separately whether files were installed and whether the application displayed the pet. If installation was not requested, deliver the reviewed build/preview without expanding scope.

## Manual fallback and final report

Use manual prompts/downloads only when browser control is unavailable or the user chooses that mode. Supply the current row prompt and exact filename, then resume local work once the real file exists. Login and human verification stay with the user; never request passwords, cookies or API keys. Preserve progress rather than making the user run the whole pipeline.

Report actual results, artifact locations, review/installation status and any specific unfinished step. Never claim unobserved generation, playback or activation.
