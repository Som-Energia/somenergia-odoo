# Arquitectura dels addons d'Odoo 16

Aquest document és la font de veritat del repositori per decidir **en quin addon
i en quin directori** s'ha d'implementar un canvi. Les convencions d'estil i el
procés de validació són a [desenvolupament](desenvolupament.md); les skills hi
poden enllaçar sense repetir aquesta informació.

El repositori agrupa addons instal·lables sobre Odoo 16. En l'estat actual, cada
directori de primer nivell que conté un `__manifest__.py` és un addon
independent. El nom tècnic de l'addon és el nom del directori i és també el nom
que s'utilitza a `depends`. Hi conviuen addons propis de Som Energia,
adaptacions i còpies de projectes de tercers; abans de modificar-los cal revisar
el manifest, el README i les capçaleres per preservar-ne l'autoria, la llicència
i, quan existeixi, la possibilitat de sincronitzar amb l'origen.

## Mapa actual del repositori

Aquest mapa descriu la responsabilitat que es constata al codi actual; no
substitueix el manifest ni el README de cada addon.

| Addon | Responsabilitat observada | Procedència indicada al repositori |
|---|---|---|
| `employee_documents_expiry` | Documents i llistes de comprovació d'empleats | Cybrosys Techno Solutions |
| `hr_employee_multidepartment` | Assignació de més d'un departament a empleats | Som Energia i OCA |
| `odoo_callinfo` | Trucades de CRM, endpoints d'informació i informe de trucades | Desenvolupament específic |
| `som_crm` | Adaptacions del CRM, activitats, trucades i integracions associades | Som Energia |
| `som_event` | Adaptacions de permisos, menús i tipus d'esdeveniment | Som Energia |
| `som_google_sheets_integration` | Configuració i lectura de Google Sheets | Som Energia |
| `som_openproject` | Importació d'hores d'OpenProject als parts d'hores | Som Energia |
| `som_survey` | Adaptacions de models, seguretat i controladors d'enquestes | Som Energia |
| `somenergia_custom` | Funcionalitat transversal de persones, assistència, permisos, projectes, parts d'hores, helpdesk i enquestes | Som Energia |
| `web_pivot_computed_measure` | Mesures calculades a les vistes pivot | Tecnativa i OCA |

Per localitzar un canvi:

1. Cerca primer el model, l'identificador XML, la ruta HTTP o l'asset afectat.
2. Llegeix el `__manifest__.py`, el `__init__.py` arrel i els imports del paquet
   corresponent.
3. Comprova els tests i les dades del mateix addon, i també l'addon que aquest
   estén mitjançant `_inherit` o `inherit_id`.
4. Confirma a `depends` que la dependència que permet l'extensió ja existeix.

Per exemple, un canvi en la importació d'OpenProject correspon a
`som_openproject`, mentre que una regla compartida de setmanes treballades que
ja defineix `somenergia_custom` s'ha de valorar primer en aquest darrer addon.
No s'ha de decidir només pel nom genèric d'un directori.

## Estructura i càrrega d'un addon

Els directoris s'afegeixen quan el mòdul els necessita, no com una plantilla
obligatòria. En modificar un addon s'ha de conservar la convenció de noms que ja
utilitza: al repositori conviuen, per exemple, `report/` i `reports/`, i hi ha
variants històriques com `wizard/`, `wizards/` i `wizzard/`. No s'han de crear
variants noves ni reanomenar-les només per homogeneïtzar.

### Fitxers arrel

- `__manifest__.py` defineix metadades, versió, dependències, fitxers de dades,
  assets, dependències externes i hooks quan pertoqui.
- `__init__.py` importa els paquets Python que Odoo ha de registrar. Un fitxer
  Python present al disc però no importat per la cadena d'`__init__.py` no queda
  registrat automàticament.
- `hooks.py`, quan existeix, conté punts d'entrada d'instal·lació declarats al
  manifest i exposats des del paquet arrel.
- `README.md` o `README.rst` documenta l'ús i la configuració específica de
  l'addon. `doc/` i `readme/` contenen documentació complementària o generada
  en alguns addons.
- `requirements.txt`, quan existeix dins de l'addon, recull requisits Python
  propis. La disponibilitat per a Odoo s'ha de contrastar també amb
  `external_dependencies` del manifest i amb la gestió de dependències de
  l'entorn.

### Codi de servidor i integracions

- `models/` conté models nous i extensions ORM. Cada fitxer nou s'importa des
  de `models/__init__.py`, i `models` des de l'`__init__.py` arrel.
- `wizard/` o `wizards/` agrupa habitualment `models.TransientModel` i les
  vistes que els obren. L'addon `odoo_callinfo` conserva el directori històric
  `wizzard/`; no és un nom a reproduir en addons nous.
- `controllers/` o `controller/` conté controladors HTTP. També necessita la
  cadena d'imports Python; cada ruta declara explícitament l'autenticació i les
  opcions aplicables.
- `report/` o `reports/` conté models Python d'informe i les vistes o plantilles
  XML relacionades. El Python s'importa i l'XML es declara al manifest.
- `pydantic/`, `json/` i `query/` són carpetes específiques que alguns addons
  actuals utilitzen per esquemes, recursos JSON o consultes SQL. No són
  convencions obligatòries d'Odoo: només s'han d'ampliar quan el mateix addon
  ja integra explícitament aquests recursos.
- `scripts/` conté utilitats operatives puntuals. Odoo no les carrega pel sol
  fet de ser en aquesta carpeta; no s'hi ha de posar lògica necessària per al
  funcionament ordinari de l'addon.

### Interfície, dades i seguretat

- `views/` conté vistes, accions i menús XML. Les extensions utilitzen
  `inherit_id` i selectors estables, en lloc de copiar la vista sencera.
- `security/ir.model.access.csv` defineix accessos per model. Altres XML de
  `security/` defineixen grups i regles de registre. Els models nous han de
  revisar ambdós nivells abans de quedar exposats.
- `data/` conté registres inicials, plantilles i accions planificades. Els
  fitxers que s'han de carregar s'enumeren a `data` del manifest; l'ordre de la
  llista és l'ordre de càrrega i ha de respectar les referències entre fitxers.
  Les dades exclusives de demostració corresponen a la clau `demo`.
- `static/src/` conté JavaScript, SCSS, XML de client i altres assets. Els
  recursos del client es declaren a la clau `assets` del manifest i al paquet
  adequat, com `web.assets_backend` o `web.assets_tests`.
- `static/description/` conté la icona i la presentació de l'addon; no és el
  lloc dels assets funcionals del client.
- `i18n/` conté traduccions `.po`. Les cadenes traduïbles provenen del codi i
  dels XML de l'addon.

Un fitxer XML o CSV no es carrega només perquè sigui a `views/`, `security/` o
`data/`: ha d'aparèixer al manifest. De manera anàloga, el codi Python depèn
dels imports. Aquesta distinció és essencial quan s'afegeix, es mou o es
renomena un fitxer.

### Tests i migracions

- `tests/` conté tests de servidor. Els mòduls que formen part de la suite
  s'importen des de `tests/__init__.py` i utilitzen les classes i els tags
  d'`odoo.tests`. Els tests web poden viure a `static/src/test/` i carregar-se
  en un paquet d'assets de test.
- `migrations/<versio>/` conté scripts associats a una versió concreta del
  manifest. Els scripts actuals utilitzen entrades com
  `post-migrate.py` amb `migrate(cr, version)`.

La selecció i la comanda de tests són a la skill
[`odoo-test`](../.agents/skills/odoo-test/SKILL.md). Els criteris per decidir si
un canvi necessita versió o migració són a
[desenvolupament](desenvolupament.md#versions-i-migracions).

## Manifests, dependències i versions

El manifest és un diccionari Python. Les claus observades tenen aquestes
responsabilitats:

- `name`, `summary`, `description`, `author`, `website`, `category` i `license`
  descriuen l'addon. La llicència no s'ha d'inferir de la resta del repositori.
- `depends` conté noms tècnics d'addons que han d'estar disponibles i
  instal·lar-se abans. `base`, `crm`, `survey` o `event` són exemples de
  dependències d'Odoo; altres noms provenen d'aquest repositori o d'altres
  repositoris presents a l'entorn.
- `data` i `demo` controlen la càrrega de dades; `assets`, els paquets web.
- `external_dependencies` declara dependències no resoltes com addons, per
  exemple paquets Python.
- `post_init_hook` i altres hooks suportats per Odoo apunten a funcions
  importades pel paquet.
- `installable`, `application` i `auto_install` expressen el comportament
  d'instal·lació. No s'ha de donar per fet un valor explícit si el manifest no
  el declara.

Abans d'afegir una dependència, cal comprovar la direcció existent entre
mòduls, que l'addon estigui disponible als entorns objectiu i que no es creï un
cicle. Una funcionalitat d'integració que necessita dos addons independents pot
correspondre a un addon pont en comptes de fer que un dels dos depengui de
l'altre.

Al repositori hi ha dues formes de versió constatades:

- versions alineades amb Odoo/OCA, com `16.0.1.0.0`;
- versions històriques curtes, com `0.1`.

Això és una descripció de l'estat actual, no una invitació a convertir formats
en un canvi no relacionat. S'ha de mantenir el patró de l'addon afectat. Quan hi
ha una migració, el nom del directori coincideix amb la nova versió completa
del manifest, com mostren les migracions de `somenergia_custom`.

## Models i patrons d'Odoo 16

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
- `_inherit` amplia un model existent; `_name` defineix un model nou. Alguns
  models del repositori combinen `_name` i `_inherit` o herència múltiple, de
  manera que cal revisar el patró concret abans de modificar-lo.
- `self.env` dona accés als models, l'usuari i el context.
- Els mètodes han de respectar si operen sobre un registre (`ensure_one()`) o
  sobre un recordset.
- Els camps calculats declaren les dependències amb `@api.depends`; els canvis
  interactius de formulari poden usar `@api.onchange` quan correspongui.

Els patrons transversals constatats inclouen extensions petites dels models
estàndard, addons d'integració separats (`som_openproject` i
`som_google_sheets_integration`), hooks postinstal·lació per ajustar dades
inicials, cron en XML, informes amb model Python i vista XML, i migracions
versionades. Cal reutilitzar el patró més proper dins del mateix addon, no
aplicar-ne un indiscriminadament a tots.

## Nou addon o ampliació d'un addon existent

La decisió es pren per responsabilitat, dependències i cicle de vida, no per la
quantitat inicial de fitxers.

**Amplia un addon existent** quan el canvi:

- forma part inequívoca de la responsabilitat que mostra el seu manifest i el
  seu codi;
- estén models o vistes que l'addon ja depèn i prova;
- s'ha d'instal·lar, actualitzar i desplegar sempre amb aquella funcionalitat;
- no introdueix una integració o un conjunt de dependències opcionals aliè a la
  resta de l'addon.

**Valora un addon nou** quan el canvi:

- té una responsabilitat funcional separable i un nom tècnic clar;
- integra un servei extern o connecta addons que poden existir per separat;
- afegiria dependències pesants o opcionals a un addon que no les necessita;
- necessita poder-se instal·lar, provar, actualitzar o desactivar de manera
  independent;
- actua com a pont i evita invertir una dependència o crear un cicle.

Abans de crear-lo, cal verificar que la funcionalitat no existeixi en Odoo, en
els repositoris OCA disponibles o en els altres repositoris de l'entorn, i
confirmar qui n'és el propietari funcional. Un addon nou només necessita les
carpetes que realment usa; aquest repositori no defineix ni necessita un
`odoo-module-scaffold` propi.

Si cap addon té una responsabilitat prou clara, això és una decisió
d'arquitectura i no s'ha de resoldre acumulant codi automàticament a
`somenergia_custom`.

## Relació amb altres repositoris i `addons_path`

Un addon no queda disponible perquè el seu repositori sigui al mateix arbre de
fitxers. Odoo només descobreix addons sota els directoris configurats a
`addons_path`; després, `depends` en resol els noms tècnics. Per tant:

- el directori arrel d'aquest repositori ha de ser una entrada d'`addons_path`;
- totes les dependències externes del manifest han d'existir en alguna altra
  entrada;
- els noms tècnics han de ser únics en el conjunt carregat: no s'ha de confiar
  en l'ordre d'`addons_path` per mantenir dues implementacions amb el mateix
  nom;
- afegir una dependència al manifest i afegir un checkout a `addons_path` són
  accions diferents, i la segona pertany a la configuració de cada entorn.

En la configuració local consultada per documentar aquest repositori s'observa
la composició següent:

1. repositoris específics de Som Energia: aquest repositori,
   `punt-somenergia` i un repositori privat;
2. checkouts funcionals de la comunitat OCA, com `crm`, `hr`, `helpdesk`,
   `project`, `queue` o `web`;
3. els directoris d'addons del nucli d'Odoo.

Aquesta llista és una **observació de l'entorn de desenvolupament actual**, no
una garantia que tots els desplegaments tinguin els mateixos repositoris ni el
mateix ordre. Les rutes absolutes, bases de dades i opcions locals no són
configuració canònica i no s'han de copiar a documentació, manifests o codi.
La configuració compartida tampoc s'ha de modificar per resoldre una tasca d'un
addon.

Els manifests mostren aquesta relació: per exemple, `somenergia_custom` depèn
d'addons d'Odoo, d'OCA, de `hr_employee_multidepartment`, de `som_survey` i
d'addons específics disponibles en altres repositoris; `som_crm` depèn tant
d'addons d'aquest repositori com d'addons externs. El manifest expressa el
contracte; la ubicació física concreta la resol l'entorn.

## Diferències amb OpenERP

Aquest és un repositori d'**Odoo 16**. Encara que es trobi codi històric en
altres projectes, no s'hi han d'introduir patrons d'OpenERP:

- el manifest és `__manifest__.py`, no `__openerp__.py`;
- s'importa des d'`odoo`, no des d'`openerp`;
- els models deriven de `models.Model` o `models.TransientModel`; no s'utilitzen
  `osv.osv`, `_columns` ni `fields.function`;
- els mètodes treballen amb recordsets i `self.env`; no usen signatures amb
  `cr`, `uid`, `ids` ni decoradors de l'API antiga;
- les extensions de vistes, la seguretat i els controladors han de seguir les
  APIs d'Odoo 16;
- els recursos web es declaren als paquets `assets` del manifest i segueixen
  l'arquitectura JavaScript d'Odoo 16, incloent mòduls Odoo i OWL quan
  correspongui, no els carregadors ni widgets de clients antics;
- les migracions segueixen els punts d'entrada i l'estructura observats en
  aquests addons, no scripts copiats d'una versió d'OpenERP.

Que un XML o un nom de model s'assembli al d'una versió antiga no garanteix
compatibilitat. Abans de portar codi, cal contrastar els camps, els mètodes, els
identificadors XML, els permisos i els assets amb Odoo 16 i amb les dependències
reals de l'entorn.

## Seguretat i límits transversals

Els models nous defineixen els accessos necessaris i, quan cal, grups o regles
de registre. `sudo()` evita les comprovacions d'accés i només és acceptable
quan el cas d'ús ho requereix i les dades afectades estan delimitades.

Els controladors declaren de manera explícita autenticació, mètodes i protecció
CSRF adequats. Ni controladors, ni scripts, ni dades, ni logs han d'incorporar
tokens, credencials, rutes personals o dades personals innecessàries. La
configuració d'integracions pertany a l'entorn o als models de configuració que
ja defineixi l'addon, no al manifest ni a aquesta documentació.
