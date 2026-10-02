---
name: git-pr
description: >
  Crea o actualitza Pull Requests seguint la política versionada de Som Energia.
  Trigger: Quan necessites crear o actualitzar una Pull Request.
metadata:
  author: oriol, pau
  version: "1.1"
---

## When to Use

Utilitza aquesta skill quan:
- Has acabat de treballar en una branca i vols crear una PR.
- Necessites actualitzar el contingut o les metadades d'una PR existent.

## Font canònica

Abans de preparar la PR, llegeix
[`.github/pull_request_template.md`](../../../.github/pull_request_template.md).
La plantilla conté la política versionada de títol, idioma, traçabilitat,
etiquetes, assignació i comprovacions. No hi afegeixis requisits que no hi
constin.

## Workflow

### Pas 1: Determinar el repositori i la branca base

Confirma el remot, el repositori de GitHub i la branca base acordada per a la
tasca. Si no se n'ha indicat cap, usa la branca per defecte publicada per
GitHub; no assumeixis silenciosament que és `main`.

```bash
git remote get-url origin
gh repo view --json nameWithOwner,defaultBranchRef
git branch --show-current
git fetch origin
```

Atura't si ets a la branca base, si la branca base acordada no existeix a
`origin` o si el remot no correspon al repositori esperat.

### Pas 2: Validar estat, commits i abast

Substitueix `<base>` per la branca base confirmada. La comparació ha de partir
de la branca remota actualitzada, no d'una referència local potencialment
obsoleta.

```bash
git status --short --branch
git log --oneline "origin/<base>..HEAD"
git diff --name-status "origin/<base>...HEAD"
git diff --stat "origin/<base>...HEAD"
git diff --check "origin/<base>...HEAD"
```

Comprova que:
- no hi ha canvis locals pendents ni fitxers staged;
- tots els commits i fitxers són de la tasca;
- el diff no conté canvis aliens ni errors de whitespace;
- la PR tindrà commits propis respecte de la base correcta.

Revisa també el diff complet amb `git diff "origin/<base>...HEAD"`. Atura't
davant canvis aliens o una base dubtosa; no els descartis ni els incorporis a
la PR.

### Pas 3: Executar i documentar comprovacions

Llegeix `AGENTS.md` i les instruccions aplicables als fitxers modificats.
Executa només els tests, linters o validacions disponibles i rellevants. No
inventis comandes ni afirmis que una comprovació ha passat si no s'ha
executat.

A la plantilla:
- usa `[x]` només per a comprovacions executades amb èxit i indica la comanda i
  el resultat;
- enumera explícitament les comprovacions no executades o no aplicables i el
  motiu;
- no presentis una comprovació no executada com a superada.

### Pas 4: Preparar metadades i descripció

Consulta les etiquetes existents i comprova si ja hi ha una PR per a la
branca:

```bash
gh label list
gh pr list --head "$(git branch --show-current)" --state all
gh api user --jq .login
```

Segueix literalment la política de
[`.github/pull_request_template.md`](../../../.github/pull_request_template.md):

1. Escriu un títol clar i descriptiu en català, sense exigir emoji ni copiar
   el nom o el format de la branca.
2. Escriu el cos en català i omple totes les seccions.
3. Enllaça OpenProject quan hi hagi una targeta; si no, enllaça la incidència
   de GitHub corresponent.
4. Afegeix només etiquetes existents adequades a la naturalesa del canvi.
5. Assigna la PR a l'autor que l'obre.

Copia la plantilla a un fitxer temporal fora del repositori, omple-la sense
esborrar-ne les seccions i revisa el resultat. No facis commit del cos omplert.

### Pas 5: Publicar i crear o actualitzar la PR

Publica la branca només després que les validacions anteriors siguin
correctes:

```bash
git push -u origin "$(git branch --show-current)"
```

Si no existeix cap PR per a la branca, crea-la indicant explícitament base,
assignació, etiqueta, títol i fitxer de cos:

```bash
gh pr create \
  --base "<base>" \
  --assignee "@me" \
  --label "<etiqueta-existent>" \
  --title "<títol clar i descriptiu en català>" \
  --body-file "/tmp/<cos-pr>.md"
```

Si ja existeix, actualitza-la en lloc de crear-ne una de duplicada:

```bash
gh pr edit "<numero>" \
  --base "<base>" \
  --add-assignee "@me" \
  --add-label "<etiqueta-existent>" \
  --title "<títol clar i descriptiu en català>" \
  --body-file "/tmp/<cos-pr>.md"
```

Finalment, verifica que la PR apunta a la base correcta, conté només els
commits i fitxers revisats i mostra les metadades esperades:

```bash
gh pr view --json url,title,body,baseRefName,headRefName,commits,files,labels,assignees
```

## Errors comuns

| Error | Acció segura |
|---|---|
| La base o el remot no són els esperats | Atura't i confirma'ls abans de publicar. |
| Hi ha canvis locals o fitxers aliens | Atura't; no els descartis ni els incloguis. |
| Una comprovació no s'ha executat | Indica-la com a no executada o no aplicable amb el motiu. |
| L'etiqueta no existeix | Consulta `gh label list`; no n'inventis cap. |
| Ja hi ha una PR per a la branca | Actualitza-la amb `gh pr edit`. |
| Fallen validacions o `git diff --check` | Corregeix els errors abans de crear o actualitzar la PR. |
