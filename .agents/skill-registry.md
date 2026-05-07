# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

See `_shared/skill-resolver.md` for the full resolution protocol.

## User Skills

> **Configuració inicial** (executar una vegada):
> ```bash
> cd $HOME/.config/opencode/skills
> ln -s $HOME/somenergia/src/somenergia-odoo/.agents/skills somenergia-odoo
> ```
> OpenCode cercarà `.agents/skills/` dins del projecte.

| Trigger | Skill | Path |
|---------|-------|------|
| Quan necessites crear una branca nova per treballar | git-branch | .agents/skills/git-branch/SKILL.md |
| Quan necessites fer un commit de codi | git-commit | .agents/skills/git-commit/SKILL.md |
| Quan necessites crear una Pull Request | git-pr | .agents/skills/git-pr/SKILL.md |

## Compact Rules

### git-branch
- Format de branca: `<type>_<description>` (ex: `ADD_user_registration`)
- Tipus: IMP_ (millora), FIX_ (bug), MOD_ (canvi), ADD_ (nova), REF_ (refactor), TEST_, DOCS_, CI_
- Descripció: 2-3 paraules en anglès, lowercase, max 50 caràcters
- Separador: guió baix entre tipus i descripció
- Sempre fer `git fetch origin && git pull origin main` abans de crear branca

### git-commit
- Format: `<emoji> <type>: <description>` (ex: `✨ feat: add user auth`)
- Tipus: feat, fix, refactor, perf, test, docs, style, chore, build, ci, revert
- Emoji obligatori seguit d'un espai
- Descripció en anglès, max 72 caràcters, imperatiu
- Context: utilitzar per guardar canvis implementats

### git-pr
- PLANTILLA OBLIGATÒRIA: Omplir totes les seccions (Objectiu, Targeta, Comportament antic, Comportament nou, Comprovacions)
- Totes les sections: Omple-les totes, no deixis espais buits
- Idioma: Català per a la descripció
- Títols: Clar i descriptiu

## Project Conventions

| File | Path | Notes |
|------|------|-------|
| AGENTS.md | AGENTS.md | Index — references files below |
| .github/docs/estil.md | .github/docs/estil.md | Estil de codi |
| .github/docs/evitar.md | .github/docs/evitar.md | Evitar patrons |
| .github/docs/arquitectura.md | .github/docs/arquitectura.md | Arquitectura |
| .github/docs/desenvolupament.md | .github/docs/desenvolupament.md | Desenvolupament |
| pull_request_template.md | pull_request_template.md | Plantilla PR |

Read the convention files listed above for project-specific patterns and rules. All referenced paths have been extracted — no need to read index files to discover more.
