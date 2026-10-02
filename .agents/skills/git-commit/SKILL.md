---
name: git-commit
description: >
  Crea commits seguint les convencions de gitmoji.dev.
  Trigger: Quan necessites fer un commit de codi.
metadata:
  author: oriol, pau
  version: "1.3"
---

## When to Use

Utilitza aquesta skill quan:
- Has fet canvis que vols guardar en un commit
- Necessites seguir la convenció de commits del projecte
- Vols preparar només els fitxers de l'abast acordat

## Format de Commit

[gitmoji.dev](https://gitmoji.dev/) és la font canònica del significat dels
emojis.

El format és: `<emoji> <description>`

L'emoji indica el tipus de commit; no cal duplicar la informació amb un type
textual com `feat:` o `fix:`.

### Selecció habitual

| Emoji | Significat oficial |
|-------|---------------------|
| ✨ | Introduir funcionalitat nova |
| 🐛 | Corregir un bug |
| 🩹 | Fer una correcció senzilla i no crítica |
| 👔 | Afegir o actualitzar lògica de negoci |
| 🗃️ | Fer canvis relacionats amb la base de dades |
| 🏗️ | Fer canvis arquitectònics |
| 🔧 | Afegir o actualitzar fitxers de configuració |
| 👷 | Afegir o actualitzar el sistema de CI |
| 📝 | Afegir o actualitzar documentació |
| ⚡️ | Millorar el rendiment |
| ♻️ | Refactoritzar codi |
| 🎨 | Millorar l'estructura o el format del codi |
| 🔥 | Eliminar codi o fitxers |
| ⚰️ | Eliminar codi mort |
| 🦺 | Afegir o actualitzar validacions |
| ✅ | Afegir, actualitzar o fer passar tests |
| 🚧 | Marcar treball en curs |
| ⬆️ | Actualitzar dependències a versions superiors |
| 🌐 | Internacionalització i localització |
| 💄 | Afegir o actualitzar la interfície i els fitxers d'estil |
| 🔨 | Afegir o actualitzar scripts de desenvolupament, incloses migracions |

Per a qualsevol emoji no llistat, consulta [gitmoji.dev](https://gitmoji.dev/)
en lloc d'inventar o redefinir-ne el significat.

### Regles

1. **Idioma**: Tota la descripció en anglès
2. **Longitud màxima**: 72 caràcters
3. **Imperatiu**: Descripció en forma imperativa (`add feature`, no `added feature`)
4. **Emoji**: Obligatori, seguit d'un espai
5. **Sense type textual**: No escriure `feat:`, `fix:` ni equivalents

## Workflow

### Pas 1: Verificar els canvis

```bash
git status --short
git diff
git diff --cached
```

Identifica els fitxers de l'abast acordat. No descartis ni incloguis canvis
aliens, i no utilitzis staging global. Si ja hi ha canvis preparats, atura't i
demana confirmació abans de continuar: no modifiquis l'índex ni desfés la
selecció preparada per l'usuari.

### Pas 2: Preparar fitxers explícits

Si cada fitxer només conté canvis de la tasca, prepara'ls explícitament:

```bash
git add <fitxer> [<fitxer> ...]
git diff --cached
git diff --cached --check
```

Si un fitxer barreja canvis de la tasca i canvis aliens, no preparis el fitxer
complet. Només amb la confirmació de l'usuari, selecciona els hunks de la tasca:

```bash
git add -p -- <fitxer>
```

Revisa cada hunk abans d'acceptar-lo. Si els canvis no es poden separar amb
seguretat per hunks, atura't. Comprova sempre que el diff preparat només conté
canvis de l'abast; si hi detectes canvis aliens, atura't i demana confirmació
sense modificar l'índex.

### Pas 3: Executar les comprovacions disponibles

Executa només les comprovacions aplicables que estiguin configurades realment
al repositori. Revisa'n abans la documentació i els fitxers de configuració;
no inventis ordres ni afirmis que una comprovació no executada ha passat.

Si una comprovació modifica fitxers, revisa `git status --short` i `git diff`,
torna a preparar explícitament només els fitxers de l'abast i repeteix:

```bash
git diff --cached
git diff --cached --check
```

### Pas 4: Crear el commit

```bash
git commit -m "<emoji> <description>"
```

### Pas 5: Verificar el resultat

```bash
git show --stat --oneline HEAD
git status --short
```

Confirma que el commit conté només els fitxers esperats i que l'estat final no
ha canviat ni eliminat canvis locals aliens.

## Exemples

```bash
# Nova funcionalitat
git commit -m "✨ add user authentication flow"

# Bug fix
git commit -m "🐛 resolve null pointer in invoice calculation"

# Refactor
git commit -m "♻️ extract payment logic to service"

# Tests
git commit -m "✅ add unit tests for contract validation"

# Documentació
git commit -m "📝 update API endpoint documentation"

# Millora de rendiment
git commit -m "⚡️ optimize database query performance"

# Estil de codi
git commit -m "🎨 format code with autopep8"

# Actualització de dependències
git commit -m "⬆️ upgrade build dependencies"

# Script de migració
git commit -m "🔨 migrate contract status values"
```

## Errors Comuns

| Error | Causa | Solució |
|-------|-------|----------|
| Nothing to commit | No hi ha fitxers preparats | Revisa `git status --short` i prepara fitxers explícits amb `git add <fitxer>` |
| Existing staged changes | L'usuari ja havia preparat canvis | Atura't, preserva l'índex i demana confirmació abans de continuar |
| Mixed task and unrelated edits | Un fitxer combina canvis de diferents abasts | Amb confirmació, usa `git add -p -- <fitxer>`; si no es poden separar amb seguretat, atura't |
| Unrelated changes staged | El diff preparat conté canvis fora de l'abast | Atura't i demana confirmació sense modificar l'índex |
| Commit message too long | Descripció massa llarga | Redueix-la a un màxim de 72 caràcters |
| No emoji | Falta l'emoji inicial | Utilitza un emoji definit a gitmoji.dev |

## Integració amb SDD

Aquesta skill s'utilitza a les fases:
- `sdd-apply`: Per guardar canvis implementats
- `sdd-verify`: Per guardar correccions
