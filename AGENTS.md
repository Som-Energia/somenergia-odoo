# Instruccions per a agents

Aquest fitxer és el punt d'entrada breu per treballar a `somenergia-odoo`. El
repositori conté addons per a **Odoo 16**; no s'hi han d'aplicar patrons de
l'antic OpenERP.

## Documentació canònica

- [Arquitectura dels addons](docs/arquitectura.md)
- [Convencions de desenvolupament](docs/desenvolupament.md)
- [Sincronització de skills comunes](docs/sincronitzacio-skills.md)
- [Registre de skills](.agents/skill-registry.md)

La documentació tècnica general viu a `docs/`. `.github/` queda reservat a
configuració que GitHub interpreta o utilitza directament.

## Skills disponibles

| Skill | Ús |
|---|---|
| [`git-branch`](.agents/skills/git-branch/SKILL.md) | Crear una branca |
| [`git-commit`](.agents/skills/git-commit/SKILL.md) | Preparar un commit |
| [`git-pr`](.agents/skills/git-pr/SKILL.md) | Crear una pull request |
| [`odoo-test`](.agents/skills/odoo-test/SKILL.md) | Executar tests d'Odoo 16 |

Abans d'editar, cal llegir la documentació i les skills que afectin la tasca.
S'han de seguir els patrons del mòdul modificat, mantenir l'abast acordat i
executar només les comprovacions aplicables. No s'ha d'afirmar que una
comprovació ha passat si no s'ha executat.
