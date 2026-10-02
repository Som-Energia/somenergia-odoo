---
name: git-branch
description: >
  Crea branques de git seguint convencions de naming: IMP, FIX, MOD, ADD, etc.
  Trigger: Quan necessites crear una branca nova per treballar.
metadata:
  author: oriol
  version: "1.1"
---

## When to Use

Utilitza aquesta skill quan:

- Començar a treballar en una nova feature
- Corregir un bug
- Fer qualsevol canvi que requerixi una branca separada

## Convencions de Naming

El format és: `<TYPE>_<description>`

### Tipus de Branca

| Tipus | Significat | Descripció |
|-------|------------|------------|
| `IMP` | Improvement | Millora de funcionalitat existent |
| `FIX` | Bug Fix | Correcció de bug |
| `MOD` | Modification | Canvi de comportament |
| `ADD` | Addition | Afegir nova funcionalitat |
| `REF` | Refactor | Refactorització sense canvi funcional |
| `TEST` | Test | Afegir o corregir tests |
| `DOCS` | Documentation | Canvis de documentació |
| `CI` | CI/CD | Canvis a pipelines |

### Regles

1. **Descripció**: 2-3 paraules en anglès i minúscules
2. **Separador**: guió baix (`_`) entre el tipus i la descripció, i també entre
   les paraules de la descripció
3. **Longitud**: màxim 50 caràcters per al nom complet de la branca

## Workflow

### Pas 1: Revisar l'estat local

```bash
git status --short --branch
```

Abans de canviar de branca, identifica qualsevol canvi preparat, no preparat o
no versionat. Si n'hi ha, atura't i confirma què se n'ha de fer. No el
descartis, no facis `stash` ni l'arrosseguis a una altra branca sense aquesta
confirmació.

### Pas 2: Detectar o validar la branca base

```bash
git remote show origin
```

Si la tasca indica una branca base, valida que coincideixi amb la base
esperada. Si no la indica, consulta `HEAD branch` a la sortida anterior. Si no
es pot determinar de manera inequívoca, demana confirmació: no assumeixis
`main` o `master` silenciosament.

### Pas 3: Actualitzar la branca base

```bash
git fetch origin
git switch <base_branch>
git pull --ff-only origin <base_branch>
```

`--ff-only` evita crear un merge accidental. Si l'actualització no pot avançar
amb fast-forward, atura't i revisa l'historial; no forcis el pull.

### Pas 4: Crear la branca nova

```bash
git switch -c <TYPE>_<description>
```

### Pas 5: Fer canvis i commit

(Utilitza la skill `git-commit`)

### Pas 6: Fer push

```bash
git push -u origin <branch_name>
```

## Exemples

```bash
# Nova funcionalitat
git switch -c ADD_user_registration

# Millora
git switch -c IMP_payment_validation

# Bug fix
git switch -c FIX_invoice_total_calculation

# Canvi de comportament
git switch -c MOD_renewal_process

# Refactor
git switch -c REF_extract_partner_service

# Tests
git switch -c TEST_contract_validation

# Documentació
git switch -c DOCS_api_reference
```

## Errors Comuns

| Error | Causa | Solució |
|-------|-------|----------|
| Branch already exists | Branca ja existent | Confirma si cal reutilitzar-la o tria un altre nom |
| Invalid branch name | El nom no segueix el format | Usa un tipus admès i guions baixos com a separadors |
| Base branch unclear | La branca base no és inequívoca | Confirma la base abans de canviar de branca |
| Not possible to fast-forward | La base local ha divergit de la remota | Atura't i revisa l'historial; no forcis el pull |

## Integració amb SDD

Aquesta skill s'utilitza a les fases:

- `sdd-propose`: Per crear branca des del proposal
- `sdd-apply`: Per crear branca de treball
