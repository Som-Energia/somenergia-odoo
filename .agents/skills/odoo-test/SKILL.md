---
name: odoo-test
description: >
  Executa tests d'Odoo 16 del repositori amb odoo-bin i test-tags.
  Trigger: Quan necessites passar tests d'un mòdul o d'un grup concret de tests.
license: Apache-2.0
metadata:
  author: pau
  version: "1.0"
---

## When to Use

Utilitza aquesta skill quan:
- Necessites validar canvis d'un mòdul Odoo
- Vols executar un grup de tests concret amb `--test-tags`
- Vols actualitzar el mòdul i passar tests en una sola comanda

## Critical Patterns

- Activar l'entorn abans de córrer tests: `pyenv activate odoo160`
- Sempre executar amb `--stop-after-init` per evitar servidor persistent
- Per test complet de mòdul, utilitzar `-u <modul> --test-enable`
- `--test-tags` accepta una llista separada per comes de filtres
- Format de filtre: `[-][tag][/module][:class][.method]`
- Un filtre amb `-` exclou; sense `-` inclou
- Si omets `tag` en inclusió, Odoo interpreta `standard`
- Si omets `tag` en exclusió, Odoo interpreta `*`
- Evitar rutes personals; usar variables (`$ODOO_ROOT`) o rutes relatives

## Commands

### Test de mòdul (base)

```bash
pyenv activate odoo160
ODOO_ROOT="/path/to/odoo160"
python "$ODOO_ROOT/src/core/odoo-bin" \
  -c "$ODOO_ROOT/conf/odoo_som.conf" \
  --no-xmlrpc \
  --stop-after-init \
  --log-level=test \
  -d <database> \
  -u <module_name> \
  --test-enable
```

### Test filtrat per tags

```bash
pyenv activate odoo160
ODOO_ROOT="/path/to/odoo160"
python "$ODOO_ROOT/src/core/odoo-bin" \
  -c "$ODOO_ROOT/conf/odoo_som.conf" \
  --no-xmlrpc \
  --stop-after-init \
  --log-level=test \
  -d <database> \
  -u <module_name> \
  --test-enable \
  --test-tags "<spec1>,<spec2>"
```

### Exemples vàlids de `--test-tags`

```bash
# Tag concret
--test-tags "som_crm_team"

# Mòdul concret
--test-tags "/som_crm"

# Classe i mètode concrets
--test-tags ":TestCrmTeam.test_team_exclude_member_absent_same_day_with_time_gap"

# Combinació (incloure + excloure)
--test-tags "som_crm_team,-slow"
```

## Notes

- Substitueix `<database>`, `<module_name>` i `<spec1>,<spec2>` pels valors del teu entorn.
- Si només vols un subconjunt, prioritza `--test-tags` per reduir temps d'execució.
