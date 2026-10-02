# Skill Registry

Aquest registre permet descobrir les skills disponibles i injectar-ne les
regles compactes quan es delega feina. És independent de l'eina d'agents: la
font completa de cada comportament és el `SKILL.md` indicat.

## Skills disponibles

| Trigger | Skill | Path |
|---|---|---|
| Quan cal crear una branca nova | `git-branch` | [`.agents/skills/git-branch/SKILL.md`](skills/git-branch/SKILL.md) |
| Quan cal fer un commit | `git-commit` | [`.agents/skills/git-commit/SKILL.md`](skills/git-commit/SKILL.md) |
| Quan cal crear una pull request | `git-pr` | [`.agents/skills/git-pr/SKILL.md`](skills/git-pr/SKILL.md) |
| Quan cal executar tests d'un mòdul Odoo o filtrar-los per tags | `odoo-test` | [`.agents/skills/odoo-test/SKILL.md`](skills/odoo-test/SKILL.md) |

## Compact rules

Les regles següents resumeixen l'estat actual de les skills. Qualsevol canvi a
una skill s'ha de reflectir en aquest resum dins del mateix canvi.

### `git-branch`

- Format: `<type>_<description>`; tipus admesos: `IMP_`, `FIX_`, `MOD_`,
  `ADD_`, `REF_`, `TEST_`, `DOCS_` i `CI_`.
- Descripció de 2 o 3 paraules en anglès i minúscules, amb un màxim de 50
  caràcters; la skill indica guions dins de la descripció si cal.
- Abans de crear-la: `git fetch origin` i `git pull origin main`.
- Crear-la amb `git checkout -b <type>_<description>` i publicar-la amb
  `git push -u origin <branch_name>`.

### `git-commit`

- Format obligatori: `<emoji> <description>` segons
  [gitmoji.dev](https://gitmoji.dev/), sense prefix textual com `feat:` o
  `fix:`.
- Descripció en anglès, imperativa i de 72 caràcters com a màxim.
- Revisar `git status` i `git diff`, seleccionar els fitxers amb `git add` i
  crear el commit amb `git commit -m "<emoji> <description>"`.

### `git-pr`

- Abans de crear-la: revisar `git status` i `git log main..HEAD --oneline`, i
  publicar la branca.
- Descripció en català i amb totes les seccions de la plantilla plenes:
  Objectiu, Targeta o incidència, Comportament antic, Comportament nou i
  Comprovacions.
- Marcar amb `[x]` només les comprovacions que apliquen i usar un títol clar i
  descriptiu.

### `odoo-test`

- Activar l'entorn amb `pyenv activate odoo160` i definir `ODOO_ROOT` sense
  fixar rutes personals al repositori.
- Executar `python "$ODOO_ROOT/src/core/odoo-bin"` amb la configuració local,
  `--stop-after-init`, `--log-level=test`, la base de dades, `-u <module>` i
  `--test-enable`.
- Filtrar, quan calgui, amb `--test-tags "<spec1>,<spec2>"`; cada filtre té el
  format `[-][tag][/module][:class][.method]`.

## Convencions del projecte

| Document | Path | Contingut |
|---|---|---|
| Índex d'agents | [`AGENTS.md`](../AGENTS.md) | Punt d'entrada breu |
| Arquitectura | [`docs/arquitectura.md`](../docs/arquitectura.md) | Estructura i patrons d'Odoo 16 |
| Desenvolupament | [`docs/desenvolupament.md`](../docs/desenvolupament.md) | Estil, pràctiques a evitar i validació |
| Sincronització | [`docs/sincronitzacio-skills.md`](../docs/sincronitzacio-skills.md) | Divergències i control de skills comunes |

La documentació tècnica canònica és a `docs/`. `.github/` es reserva per a
configuració consumida directament per GitHub.
