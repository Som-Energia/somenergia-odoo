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

- La política canònica és [`.github/pull_request_template.md`](../.github/pull_request_template.md):
  la skill l'ha de llegir i seguir sense inventar requisits.
- Confirmar el remot i la branca base acordada o, si no s'ha indicat, detectar
  la branca per defecte amb GitHub; actualitzar `origin` abans de comparar.
- Abans de publicar: exigir un estat net i revisar commits, fitxers, estadística
  i diff complet contra `origin/<base>` amb la comparació correcta; executar
  `git diff --check origin/<base>...HEAD` i aturar-se davant canvis aliens.
- Executar només tests i checks disponibles i rellevants. Marcar amb `[x]`
  exclusivament els executats amb èxit, i enumerar explícitament els no
  executats o no aplicables amb el motiu.
- Títol clar i descriptiu en català, sense exigir emoji ni reproduir el nom o
  format de la branca; cos en català amb totes les seccions plenes.
- Enllaçar OpenProject quan existeixi una targeta; si no, enllaçar la incidència
  de GitHub corresponent.
- Afegir una etiqueta només si n'existeix una d'adequada; altrament, ometre
  l'opció d'etiqueta. Autoassignar la PR a l'autor que l'obre.
- Publicar després de validar; cercar només PRs obertes i actualitzar-ne una
  únicament si el head coincideix exactament en owner, repositori i branca. Si
  no hi ha coincidència exacta, crear una PR nova amb la base explícita.
- Verificar al final base, commits, fitxers i metadades.

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
