# Codex Various Pet

[中文说明](README.md)

**Give Codex this repository URL, a character image and a request. The agent operates your signed-in ChatGPT website and makes a local Codex desktop pet.**

No manual package or skill setup is required first. Codex reads the repository, prepares its environment, uploads the reference, generates and downloads strips, checks and retries defects, reviews the actual motion in the background, and installs the accepted result when authorized. You keep the original ChatGPT page and receive the Codex pet; no extra preview website needs your attention.

## Give this to Codex

Attach the reference in a Codex task with local terminal/file access and browser control:

> Read https://github.com/Andonis75/codex-various-pet, including README and AGENTS.md. Prepare the environment and read its various-pet skill. Turn my attached character into a Codex desktop pet named “My Cat.” Use my signed-in ChatGPT website in the in-app browser. Keep the identity and art style; generate all nine animations, download and inspect the originals, retry defects, review the motion in the background, then install the accepted build locally. Continue without asking me to say “continue” after each state or operate an extra preview page. Pause only for login, human verification or an actual missing capability, and report the final result.

Existing sketches and strips can be supplied to resume work.

**Required capabilities:** the agent must actually have a usable browser controller and local Python/terminal access. This repository does not add a browser, sign you into ChatGPT or grant image-generation quota. Missing tools must be reported truthfully.

## What the agent does

1. Reads the repository and runs `tools/bootstrap.py`, creating an isolated `.venv` and using its returned Python path.
2. Uploads the reference in the intended signed-in tab and establishes one consistent identity.
3. Generates idle first, downloads the real original, and checks decoded format and alpha before spending quota on the rest.
4. Generates the remaining strips individually. A reviewed right-run may be explicitly mirrored only when appropriate; asymmetric characters need independent left-running art.
5. Runs the pipeline internally and reviews real contact sheets, GIFs and ordered frames for identity, head scale, foot registration, gait, jump lift, clipping and transitions. Any temporary interactive preview is used internally and closed afterward; affected rows are repaired.
6. When installation was requested, records review only after viewing the current motion, verifies hashes and installs without overwriting an existing pet. File installation and observed desktop selection are reported separately.

You handle necessary login and human-verification steps. Generation depends on account permissions, subscriptions and quota. Persistent service or quality failures are reported with accepted work preserved; unattended completion across arbitrary web versions is not guaranteed. A selected web workflow is not silently replaced with a paid API.

Outputs include original strips, a transparent **1536×1872 v1 atlas**, quality records and motion-review artifacts, with an optional offline player for debugging. A painted checkerboard is not transparency, and deleting all white pixels can destroy character details.

This targets **local Codex desktop pets**, checked against `26.1013`, not ChatGPT Work cloud Pets. Official introduction: [Pets](https://learn.chatgpt.com/docs/pets). If no supported tool can operate the desktop pet selector, the agent reports the remaining selection step.

## Optional reusable skill installation

Codex can do this itself, or you may install manually with Python 3.10+:

```bash
python -m pip install "git+https://github.com/Andonis75/codex-various-pet.git"
various-pet install-skill
```

If the executable is outside PATH, use `python -m codex_various_pet install-skill`. Start a new task, attach a reference and invoke `$various-pet`. Browser capabilities still depend on the actual environment.

[Browser playbook](src/codex_various_pet/data/skill/references/browser-playbook.md) · [Nine-state prompts](src/codex_various_pet/data/skill/references/web-generation.md) · [Format](src/codex_various_pet/data/skill/references/format.md) · [Troubleshooting](src/codex_various_pet/data/skill/references/troubleshooting.md) · [Advanced CLI/manual fallback](docs/advanced-cli.md)

Code: [MIT](LICENSE). Reference images and generated artwork retain their respective rights and service terms. Do not submit credentials or private chat URLs in issues.
