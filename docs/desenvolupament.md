# Desenvolupament a `somenergia-odoo`

Aquest document concentra les convencions generals d'estil i els patrons que
cal evitar. Les decisions d'estructura i ORM són a
[arquitectura](arquitectura.md).

## Abans de modificar codi

1. Identifica l'addon afectat i llegeix-ne el manifest, els imports i els tests.
2. Busca una implementació semblant al mateix addon abans de crear un patró
   nou.
3. Limita el canvi a l'objectiu acordat i no reformatis fitxers no relacionats.
4. Comprova si el canvi afecta seguretat, dades, traduccions, assets, la versió
   del mòdul o una migració.

## Python i ORM

- Escriu codi compatible amb Python i amb l'API moderna suportats per Odoo 16.
- Indenta amb quatre espais i usa noms descriptius.
- Ordena i separa els imports de manera coherent amb el fitxer existent.
- Mantén els mètodes curts quan separar responsabilitats millori la lectura.
- Opera sobre recordsets sempre que sigui possible i evita consultes dins de
  bucles si es poden agrupar amb `search`, `mapped`, `filtered` o `read_group`.
- Usa `ensure_one()` quan el mètode requereixi exactament un registre.
- Declara totes les dependències dels camps calculats amb `@api.depends`.
- Passa canvis temporals de context amb `with_context()`; no modifiquis el
  diccionari de context compartit.
- Usa `UserError` o `ValidationError` per errors que s'han de mostrar a
  l'usuari, no excepcions genèriques.
- Afegeix `sudo()` només després de valorar permisos i regles de registre.

Cal evitar:

- l'API antiga (`osv`, `_columns`, `cursor`, `uid`, `ids`);
- SQL manual quan l'ORM resol el mateix cas de manera clara;
- capturar `Exception` sense una recuperació concreta;
- valors d'entorn, identificadors de base de dades o secrets fixats al codi;
- dependències noves sense justificar-les al manifest o als requirements de
  l'addon;
- abstraccions especulatives que només tenen un ús.

Si una consulta SQL és necessària per volum o per una operació que l'ORM no
expressa bé, ha d'estar parametritzada i el codi ha de deixar clar per què no
s'utilitza l'ORM.

## XML, seguretat i interfície

- Usa identificadors XML estables, descriptius i amb el prefix del mòdul quan
  pugui haver-hi ambigüitat.
- Prefereix heretar una vista i modificar-ne el fragment necessari a copiar-la
  sencera.
- Mantén les dades, vistes i accessos en fitxers separats segons la convenció
  de l'addon.
- No exposis un model nou sense revisar els accessos i les regles de registre.
- Escapa el contingut dinàmic i no relaxis autenticació o CSRF per resoldre un
  problema puntual.
- En JavaScript, reutilitza els serveis i registres d'Odoo 16; no introdueixis
  globals ni APIs del client d'altres versions.

Cal evitar selectors d'herència fràgils, duplicar vistes completes, donar
permisos amplis per defecte i incloure secrets o dades personals en XML,
fixtures, logs o captures.

## Tests

Els canvis funcionals han d'anar coberts pel test més proper al comportament:

- `TransactionCase` per lògica de models i transaccions;
- tests HTTP per rutes i permisos;
- tests web per comportament del client quan no es pot validar al servidor.

Els tests han de ser deterministes, crear només les dades necessàries i
verificar tant el resultat com els permisos o efectes laterals rellevants. No
s'han de desactivar assertions, amagar errors amb captures genèriques ni fer
dependre una prova de l'ordre d'execució.

Per executar-los, segueix [`odoo-test`](../.agents/skills/odoo-test/SKILL.md).
La base de dades i les rutes de l'entorn són paràmetres locals: no s'han de
fixar al repositori.

## Versions i migracions

Un canvi de dades o d'esquema pot requerir incrementar la versió del manifest
i crear una migració. La migració ha de:

- usar l'API d'Odoo 16 i el punt d'entrada esperat pel projecte;
- ser explícita sobre els registres afectats;
- evitar dependències circulars noves;
- registrar informació útil sense exposar dades sensibles;
- tenir una estratègia de validació sobre una base representativa.

No copiïs scripts ni convencions de migració d'OpenERP: la seva API i el seu
format no són els d'aquest repositori.

## Git i pull requests

Les convencions operatives viuen a les skills
[`git-branch`](../.agents/skills/git-branch/SKILL.md),
[`git-commit`](../.agents/skills/git-commit/SKILL.md) i
[`git-pr`](../.agents/skills/git-pr/SKILL.md). Aquest document no les duplica;
si canvia una convenció, s'ha d'actualitzar la skill i el resum del
[registre](../.agents/skill-registry.md) conjuntament.

## Comprovacions abans d'entregar

Executa les comprovacions que corresponguin al canvi i informa del resultat
real:

- tests de l'addon afectat;
- comprovacions de sintaxi o estil disponibles a l'entorn;
- càrrega o actualització del mòdul quan canvien models, vistes o dades;
- revisió de `git diff --check` i del diff complet;
- per documentació, validació dels enllaços i paths locals.

Una comprovació no executada s'ha de marcar com a no executada, no com a
superada.
