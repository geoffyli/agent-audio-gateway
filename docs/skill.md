# Agent Skill Package

The skill package teaches agent systems how to use `agent-audio-gateway` through the shell.

## Location

```
skill/
├── SKILL.md              ← primary skill instructions (load this into the agent)
└── references/
    ├── cli-usage.md      ← full CLI flag reference
    ├── json-schemas.md   ← annotated JSON shapes for all responses
    └── troubleshooting.md ← common errors and fixes
```

## How to use

Load `skill/SKILL.md` into your agent system as a skill, custom instruction, or context document. The skill teaches the agent:

1. When to use the gateway (detecting relevant use cases)
2. Which command to run for which task
3. How to choose standard mode vs structured mode and parse results (`result.summary` vs `result.data`)
4. How to handle errors
5. How to avoid falling back to transcript-only reasoning

## Skill design principles

- The skill is **framework-agnostic** — it is plain markdown
- It does not encode domain-specific business logic
- It instructs the agent to treat CLI output as authoritative
- It reminds the agent not to claim it directly heard audio unless it used the gateway

## Compatibility

The skill works with any agent system that:
- Supports a skill mechanism or custom instructions
- Has access to shell execution
- Can read the target audio file path

Minor host-specific adjustments (install location, shell permissions, how skills are loaded) may be needed for specific agent platforms.

## Future extensions

Higher-level skills (speech coaching, interview analysis, etc.) should be built **on top** of this base skill — not by modifying it. The gateway skill covers the general audio capability layer; domain logic lives in downstream skills.
