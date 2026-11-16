# Sincronització de skills comunes

La configuració d'agents d'aquest repositori parteix de la d'
[`openerp_som_addons`](https://github.com/Som-Energia/openerp_som_addons/tree/main/.agents),
però no se'n pot copiar el contingut sense adaptar-lo: aquell projecte usa
OpenERP 5 i aquest usa Odoo 16.

## Relació actual

| Skill local | Referència | Estat i divergència intencionada |
|---|---|---|
| `git-branch` | `git-branch` | Comuna. La revisió funcional del contingut queda fora d'aquesta adaptació documental. |
| `git-commit` | `git-commit` | Comuna. La revisió funcional del contingut queda fora d'aquesta adaptació documental. |
| `git-pr` | `git-pr` | Comuna. La revisió funcional del contingut queda fora d'aquesta adaptació documental. |
| `odoo-test` | `erp-test` | Específica d'Odoo 16: usa `odoo-bin` i tags d'Odoo, no Destral ni la infraestructura d'OpenERP. |

Les altres skills de la referència no es consideren comunes automàticament.
Algunes depenen de l'arquitectura d'OpenERP, de repositoris auxiliars o de
workflows que no existeixen aquí. Només s'han d'incorporar quan hi hagi un cas
d'ús verificat i una adaptació explícita a Odoo 16.

Les tres skills de Git mantenen de moment les diferències existents. Les seves
revisions de comportament corresponen respectivament a les issues `#111`,
`#112` i `#113`; l'issue `#110` només en manté el registre fidel a l'estat
actual.

## Punt de control de la referència

Última revisió: 2026-10-02.

| Skill de referència | Darrer commit que la modificava en revisar-la |
|---|---|
| `git-branch` | `38a9edb66f6ec06bf4581460be9a39e9a988bc2c` |
| `git-commit` | `680a310b6776cfb5773a9bc7607a5ce4e92a9756` |
| `git-pr` | `38a9edb66f6ec06bf4581460be9a39e9a988bc2c` |

## Comprovació lleugera

Per saber si una skill comuna ha canviat a la referència, des de l'arrel
d'aquest repositori:

```bash
for skill in git-branch git-commit git-pr; do
    printf '%-12s ' "$skill"
    gh api \
        "repos/Som-Energia/openerp_som_addons/commits?path=.agents/skills/$skill/SKILL.md&per_page=1" \
        --jq '.[0].sha'
done
```

Cal comparar el resultat amb la taula anterior. Si canvia algun hash:

1. llegeix el diff de la skill de referència;
2. classifica cada canvi com a comú o específic d'OpenERP;
3. adapta només les parts comunes a Odoo 16;
4. actualitza alhora la skill local, les seves compact rules del
   [registre](../.agents/skill-registry.md) i el hash d'aquesta pàgina;
5. comprova que tots els paths documentats existeixen i que no s'han introduït
   ordres o terminologia d'OpenERP.

Un hash diferent és un avís de revisió, no una ordre de copiar. Les
divergències justificades s'han d'afegir a la taula de relació perquè una
revisió futura no les interpreti com una desactualització accidental.
