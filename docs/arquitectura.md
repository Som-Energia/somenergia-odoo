# Arquitectura dels addons d'Odoo 16

Aquest repositori agrupa addons instal·lables sobre Odoo 16. Cada directori de
primer nivell que conté un `__manifest__.py` és un addon independent. Alguns
addons són propis de Som Energia i d'altres provenen de projectes de tercers;
cal preservar l'autoria i la llicència de cada mòdul.

## Estructura d'un addon

Els directoris s'afegeixen quan el mòdul els necessita, no com a estructura
obligatòria:

- `__manifest__.py`: metadades, dependències, dades, assets i versió.
- `__init__.py`: importació dels paquets Python del mòdul.
- `models/`: models i extensions de models amb l'ORM d'Odoo.
- `views/`: vistes, menús i accions XML.
- `wizard/` o `wizards/`: models transitoris i les seves vistes.
- `controllers/` o `controller/`: controladors HTTP.
- `reports/` o `report/`: models i plantilles d'informes.
- `data/`: dades inicials i tasques planificades.
- `security/`: grups, regles i accessos de models.
- `migrations/`: scripts vinculats a una versió del mòdul.
- `tests/`: tests Python d'Odoo.
- `static/`: assets web i descripció del mòdul.
- `i18n/`: traduccions.

En modificar un addon s'ha de conservar la convenció de noms que ja utilitza.
No s'han de crear variants noves de carpetes només per homogeneïtzar-lo.

## Models i ORM

Els models utilitzen l'API d'Odoo 16:

```python
from odoo import api, fields, models


class ExampleModel(models.Model):
    _inherit = "res.partner"

    example_code = fields.Char()
    example_label = fields.Char(compute="_compute_example_label")

    @api.depends("example_code")
    def _compute_example_label(self):
        for record in self:
            record.example_label = record.example_code or ""
```

- `models.Model` defineix models persistents i `models.TransientModel`,
  assistents temporals.
- `_inherit` amplia un model existent; `_name` defineix un model nou.
- `self.env` dona accés als models, l'usuari i el context.
- Els mètodes han de respectar si operen sobre un registre (`ensure_one()`) o
  sobre un recordset.
- Els camps calculats han de declarar dependències correctes amb
  `@api.depends`; els canvis interactius de formulari poden usar
  `@api.onchange` quan correspongui.

No s'han d'introduir `osv.osv`, `_columns`, `fields.function` ni signatures amb
`cursor, uid, ids`: són patrons d'OpenERP i no d'Odoo 16.

## Manifest, dades i assets

El manifest és un diccionari Python a `__manifest__.py`. La clau `depends`
expressa les dependències entre addons; `data` enumera els XML i CSV que es
carreguen, i `assets` declara els recursos web. Qualsevol fitxer que Odoo hagi
de carregar ha de quedar registrat al manifest o importat des del paquet
corresponent.

Abans d'afegir una dependència, cal comprovar la direcció existent entre
mòduls i evitar cicles. Una funcionalitat d'integració que necessita dos
mòduls independents pot requerir un mòdul pont en comptes d'invertir una
dependència.

## Seguretat

Els models nous han de definir els accessos necessaris a
`security/ir.model.access.csv` i, quan calgui, grups o regles de registre. L'ús
de `sudo()` evita les comprovacions d'accés i només és acceptable quan el cas
d'ús ho requereix i s'han delimitat les dades afectades.

Els controladors han de declarar de manera explícita l'autenticació, els
mètodes i la protecció CSRF adequats per a la ruta. No s'han de registrar als
logs tokens, credencials ni dades personals innecessàries.

## Vistes i client web

Les vistes XML, accions i menús segueixen l'arquitectura d'Odoo 16. Les
extensions de vista han d'usar `inherit_id` i selectors prou estables. Els
assets JavaScript d'aquest repositori són mòduls ES d'Odoo 16 i, quan
correspongui, components OWL; s'han de declarar al paquet d'assets adequat del
manifest.

## Migracions

Quan un canvi de model o de dades ho necessita, la versió del manifest s'ha
d'incrementar i s'ha d'afegir el script sota
`<modul>/migrations/<versio>/`. Els scripts existents utilitzen els punts
d'entrada d'Odoo, com `migrate(cr, version)`, i han de poder executar-se de
manera segura sobre l'estat esperat de la base de dades.

## Tests

Els tests viuen dins de `<modul>/tests/`, s'importen des del seu `__init__.py`
i utilitzen les classes de `odoo.tests.common`. Els tags amb `@tagged(...)`
permeten seleccionar suites concretes. La comanda i els filtres vigents es
documenten a la skill [`odoo-test`](../.agents/skills/odoo-test/SKILL.md).
