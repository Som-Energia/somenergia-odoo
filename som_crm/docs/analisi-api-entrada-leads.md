# Anàlisi de l’API d’entrada de leads

## 1. Objectiu i abast

Aquest document descriu el comportament actual de `POST /api/crm/lead` del
mòdul `som_crm`, sobre Odoo 16 Community, per preparar l’entrada de leads des
d’un nou sistema extern.

L’estudi es basa en la lectura del controlador, els models personalitzats,
les dades XML, les plantilles, els tests i el codi local del framework.
No s’han executat peticions, tests ni consultes a la base de dades durant
l’estudi. No acredita la configuració efectiva de producció ni totes les
extensions que hi pugui haver instal·lades.

**Conclusió principal:** l’endpoint crea directament una oportunitat i executa
un flux de captació web. La presència de qualsevol adjunt determina un canal,
una etapa i una confirmació de recepció de factura per fer-ne una simulació.
No és només una operació genèrica d’inserció de leads.

Al llarg del document es distingeixen:

- **Comportament verificat:** implementació observada al codi local.
- **Configuració pendent de verificar:** valors efectius de la base de dades.
- **Recomanacions:** propostes per a l’ampliació, encara no implementades.

## 2. Fonts i punts d’entrada

Les rutes dels enllaços són relatives a aquest document.

| Font | Responsabilitat |
| --- | --- |
| [Controlador](../controller/main.py) | HTTP, autenticació, entrada, validació, adjunts i orquestració |
| [Model `crm.lead`](../models/crm_lead.py) | Assignació, activitats, contactes, UTM, correus i processos posteriors |
| [Model `crm.team`](../models/crm_team.py) | Selecció del comercial elegible |
| [Model `res.users`](../models/res_users.py) | Capacitat i exclusions d’assignació |
| [Model `res.company`](../models/res_company.py) | Configuració funcional per empresa |
| [Dades inicials i crons](../data/data.xml) | Canals, tipus d’activitat i tasques planificades |
| [Etapes](../data/crm_stage_data.xml) | Etapes personalitzades |
| [Plantilles de confirmació](../data/mail_template_data.xml) | Contingut i destinatari dels correus |
| [Tests HTTP](../tests/test_api_crm.py) | Casos existents de l’API |
| [Tests del model](../tests/test_crm_lead.py) | Casos de lògica de negoci |
| [OpenAPI del mòdul](crm_lead_api.json) | Documentació del contracte HTTP |

Hi ha una altra còpia de la documentació OpenAPI a
[`docs/crm_lead_api.json`](../../docs/crm_lead_api.json), a l’arrel del repositori.
Si s’amplia el contracte cal revisar totes dues, així com `GET /api/crm/docs`,
que genera documentació des del controlador.

## 3. Contracte HTTP i autenticació

```python
@http.route('/api/crm/lead', type='http', auth='none',
            methods=['POST'], cors='*', csrf=False)
```

La petició prevista és un `POST` amb cos JSON i capçaleres:

```http
Content-Type: application/json
X-API-Key: <clau del sistema emissor>
```

La ruta no exigeix una sessió autenticada d’Odoo. L’autenticació funcional
la fa `_authenticate_api_key()`, comparant la capçalera amb el paràmetre
`som_crm.api_key`, llegit amb `sudo()`.

- És una única clau compartida: no identifica ni diferencia sistemes emissors.
- No utilitza les API keys natives dels usuaris d’Odoo.
- El missatge de rebuig menciona autenticació al cos JSON, però aquesta via
  no està implementada.
- Les dades XML inclouen un valor inicial de clau que s’ha de substituir;
  la clau efectiva de cada entorn s’ha de comprovar sense publicar-la.
- CORS està obert a qualsevol origen i CSRF està desactivat.

L’ordre importa: **el JSON es llegeix abans de validar la clau**. Un cos
mal format pot retornar `400` encara que no s’hagi autenticat la petició.

## 4. Formats d’entrada i mapatge

### 4.1. JSON pla

Totes les dades personals i URLs dels exemples són fictícies. El telèfon és
il·lustratiu i no representa un número de contacte vàlid.

```json
{
  "contact_name": "Contacte Exemple A",
  "email": "contacte.a@example.com",
  "phone": "+34 000 000 001",
  "lang": "ca_ES",
  "url_origin": "https://example.invalid/ca/formulari/?utm_source=google&utm_medium=cpc&utm_campaign=exemple",
  "comments": "Voldria informació.\nEm podeu contactar per correu."
}
```

### 4.2. JSON amb `lead_data`

El controlador també admet aquest embolcall:

```json
{
  "lead_data": {
    "contact_name": "Contacte Exemple A",
    "email": "contacte.a@example.com"
  },
  "files": []
}
```

`lead_data`, si existeix, es pren com a conjunt de dades del lead, sense
combinar-lo amb els altres camps del primer nivell.

**Els fitxers només s’extreuen del primer nivell.** Posar `files` dins de
`lead_data` no crea adjunts. Si el `files` del primer nivell no és una llista,
es tracta com si no hi hagués fitxers, sense error explícit.

El cos HTTP, si no és buit, es descodifica com a UTF-8 i es passa a
`json.loads()`. Si no hi ha cos, es prova de llegir un paràmetre `data`, amb
`{}` com a valor per defecte. La ruta no implementa una càrrega multipart
de fitxers: els documents es transporten dins del JSON en Base64.

### 4.3. Camps acceptats

| Entrada | Destinació | Transformació |
| --- | --- | --- |
| `name` | `crm.lead.name` | Si la clau no existeix, pren el nom del contacte normalitzat |
| `contact_name` | `contact_name` | Aplica `.title()`; no elimina espais dels extrems explícitament |
| `email` | `email_from` | Aplica `.lower().strip()` |
| `phone` | `phone` | Elimina espais simples; no fa una normalització telefònica completa |
| `lang` | `lang_id` | Resol `ca_ES` o `es_ES` amb `get_lang()` |
| `url_origin` | `som_url_origin` | Desa la URL per processar-ne l’atribució |
| `comments` | Nota interna del chatter | Converteix salts de línia a `<br/>` i tabulacions a quatre espais |
| `files` | `ir.attachment` | Valida i crea els documents vinculats |

Un idioma no admès no provoca un error explícit: no se selecciona per aquesta
via. La resolució d’un idioma admès depèn també dels idiomes disponibles.

El controlador força `type='opportunity'` i `user_id=False`. No ofereix
mapatge d’entrada per a `partner_id`, `team_id`, `stage_id`, `som_channel`,
`campaign_id`, `medium_id`, `source_id`, `vat`, `som_cups`, `som_id_meta` ni
altres camps del model. Les dades addicionals poden quedar al JSON del chatter,
però no s’assignen automàticament als camps de l’oportunitat.

### 4.4. Validació efectiva

`_validate_lead_data()` té `required_fields = []` i la comprovació de format
d’email està comentada. No hi ha una validació completa de tipus ni de
l’estructura arrel del JSON.

Això no significa que qualsevol entrada completi el flux:

- L’ORM pot exigir dades com el nom de l’oportunitat.
- Per crear un contacte nou, `assign_partner()` exigeix `contact_name` i
  almenys email o telèfon, si no troba un contacte existent.
- Un `phone` numèric pot fallar en executar `.replace()`.
- Una arrel JSON que no sigui un objecte pot fallar abans de validar les dades.

Per tant, la documentació de «tots els camps opcionals» no reflecteix tots
els requisits del procés complet.

## 5. Seqüència d’execució

```text
Sistema emissor
  │ POST /api/crm/lead
  ▼
Llegir JSON i extreure files del primer nivell
  → validar X-API-Key
  → seleccionar lead_data o les dades planes
  → validar dades i fitxers
  → preparar camps, canal i etapa
  → crear crm.lead com a base.user_root (OdooBot)
      → executar el create() heretat i el personalitzat
  → auto_assign_user()
  → create_upcomming_activity(force_today=True)
  → process_utm_data()
  → crear ir.attachment, si hi ha documents
  → preparar les dades de resposta
  → publicar el JSON rebut al chatter, amb files_count
  → publicar comments com a nota interna, si existeix
  → assign_partner()
  → action_send_email_confirmation(invoice_received=bool(attachments))
  → retornar resposta JSON
```

El registre es crea amb `with_user(base.user_root)`. Els documents es creen
amb `sudo()`. L’activitat es crea amb l’usuari comercial assignat. Això fa
que els passos no operin tots amb el mateix usuari ni amb els mateixos permisos.

L’endpoint orquestra explícitament el flux: no n’hi ha prou de cridar
`crm.lead.create()` des d’una altra integració per reproduir-lo sencer.

## 6. Etapa i canal segons els adjunts

| Entrada | `som_channel` | `stage_id` | Plantilla prevista |
| --- | --- | --- | --- |
| Sense fitxers | `som_crm.som_medium_webform` | `crm.stage_lead1` | Confirmació genèrica |
| Amb fitxers | `som_crm.som_medium_webform_simulation` | `crm.stage_lead2` | Recepció de factura per simular |

Els canals es creen amb els noms `Web form` i `Web Form simulation ready`.
Les etapes es resolen per XML ID; el seu nom visible real pot haver estat
modificat a la base de dades. Les redefinicions de nom de les etapes
estàndard que apareixen a `crm_stage_data.xml` estan comentades.

Si una referència de canal no existeix, s’assigna `False`. Si no existeix
la referència d’etapa, el controlador no força `stage_id` i entra en joc el
comportament per defecte del model.

**No s’analitza el significat del document.** Un CSV o una imatge també
activen el camí de simulació i la confirmació de recepció de factura.

## 7. Assignació comercial i seguiment

### 7.1. Selecció del responsable

`auto_assign_user()` obté `sales_team.team_sales_department` i crida
`get_random_member(exclude_team_leader=True)`.

El conjunt de candidats es construeix així:

1. Parteix dels membres de l’equip.
2. Exclou el responsable de l’equip.
3. Exigeix un empleat associat i exclou els empleats amb absències que
   cobreixen la data actual. La consulta no filtra l’estat de l’absència.
4. Aplica `som_not_assign_opportunities`: sense un interval complet exclou
   l’usuari; amb interval complet l’exclou durant aquell interval, inclosos
   els extrems.
5. Si hi ha candidats amb capacitat disponible, escull aleatòriament entre
   aquests. Si no n’hi ha, escull entre tots els candidats elegibles.

La capacitat compta oportunitats actives assignades que no són guanyades.
`som_max_leads_capacity=-1` significa capacitat il·limitada.

**La capacitat no és un límit estricte ni un repartiment proporcional:** tots
els candidats amb capacitat tenen una selecció aleatòria, i si tots estan
plens encara se’n pot seleccionar un. Si no hi ha equip o candidat elegible,
l’oportunitat pot quedar sense responsable.

L’equip serveix per escollir l’usuari; aquest mètode no escriu explícitament
`team_id` a l’oportunitat. El camp queda subjecte al comportament del model.

### 7.2. Activitat inicial

`create_upcomming_activity(force_today=True)` crea una `mail.activity` de
tipus `som_crm.som_upcoming_activity`, amb venciment avui i per al responsable.
No la crea si no hi ha responsable, si falta el tipus d’activitat o si
l’etapa coincideix amb l’etapa guanyada retornada per `get_won_stage()`.

El `create()` personalitzat també intenta crear una activitat quan està
activat `som_ff_auto_upcomming_activity` i no hi ha context `from_phonecall`.
En el camí ordinari de l’API encara no hi ha responsable i aquest primer
intent no la crea. Després de l’assignació, el controlador ho torna a demanar.

**La crida explícita de l’API no consulta aquest flag d’empresa.** Desactivar-lo
no desactiva per si sol l’activitat inicial d’aquest endpoint. El mètode de
creació d’activitat tampoc comprova si ja n’hi ha una; possibles automatismes
addicionals s’han de considerar en verificar que no es dupliqui.

## 8. Atribució UTM/MTM

`process_utm_data()` processa `som_url_origin` i assigna:

| Destinació | Paràmetre prioritari | Alternativa |
| --- | --- | --- |
| `campaign_id` | `mtm_campaign` | `utm_campaign` |
| `medium_id` | `mtm_medium` | `utm_medium` |
| `source_id` | `mtm_source` | `utm_source` |

Busca per nom exacte i, si no existeix, crea el registre amb `sudo()`.
Si un paràmetre es rep diverses vegades, l’extractor pren el primer valor.

L’extractor també recull `utm_term`, `utm_content`, `mtm_keyword`,
`mtm_content`, `mtm_cid` i `mtm_group`, però aquest procés no els assigna a
camps específics. La URL original sí que queda desada.

Quan hi ha URL, els tres camps es reescriuen i els valors absents es posen
a `False`. Sense URL, el mètode no els processa.

`som_channel` i `medium_id` són independents: el primer representa el canal
d’entrada web; el segon, el mitjà d’atribució de màrqueting.

## 9. Documents adjunts

Cada document ha de ser un objecte amb `filename` i `content` en Base64.
`mimetype` és opcional. La validació aplica:

- Nom no buit i longitud màxima de 255 caràcters.
- Màxim de 10 MiB per document i 50 MiB sumant tots els documents, calculats
  sobre el contingut descodificat.
- MIME declarat pel client o deduït del nom amb `mimetypes.guess_type()`.
- Llista permesa: JPEG, PNG, GIF, BMP, WebP, PDF, Word, Excel, PowerPoint,
  text pla, CSV, ZIP i `application/x-rar-compressed`.

Els límits del codi són 10 i 50, malgrat que alguns comentaris antics
indiquen 5 i 20. El transport Base64 incrementa la mida del cos HTTP;
els límits del proxy o del servidor poden ser diferents.

La validació no inspecciona que el contingut real coincideixi amb el MIME.
`base64.b64decode()` no s’utilitza amb `validate=True`: no és una validació
estricta de tota la cadena Base64.

Cada fitxer es desa com a `ir.attachment` binari, vinculat amb
`res_model='crm.lead'` i `res_id` de l’oportunitat. La resposta inclou l’ID,
el nom, el MIME i la mida de cada adjunt creat.

## 10. Chatter i traçabilitat

Després de crear els adjunts es publica una còpia del JSON dins d’un `<pre>`,
amb `files_count`. Per al format previst, el camp `files` del primer nivell
ja s’ha extret i no s’hi inclou el contingut binari.

No és un registre byte a byte de la petició original: es reserialitza el JSON.
Tampoc no és un mecanisme d’identificació d’esdeveniments ni d’idempotència.
Si s’envien camps inesperats o `files` en una estructura no reconeguda,
aquestes dades poden acabar dins del missatge.

Els comentaris es publiquen separadament amb assumpte traduïble
`Contact form comments`, `message_type='comment'` i subtipus `mail.mt_note`.
No s’assignen al camp `description`.

La inserció dels textos es fa com a cos HTML del chatter, subjecte al
tractament d’Odoo; el controlador no fa una conversió explícita de tots
els valors d’entrada a text HTML escapat.

## 11. Associació o creació del contacte

`assign_partner()` només actua sobre oportunitats sense `partner_id`:

1. Busca un contacte amb email exactament igual a `email_from`, amb `limit=1`.
2. Si no el troba, busca per telèfon exacte, també amb `limit=1`.
3. Si el candidat per telèfon i l’oportunitat tenen email i difereixen
   ignorant majúscules, descarta aquest candidat.
4. Si no troba candidat, exigeix nom de contacte i email o telèfon i delega
   la creació a `_handle_partner_assignment(create_missing=True)` d’Odoo.

La cerca personalitzada no normalitza els valors dels contactes existents
durant la consulta, no busca per `mobile` i no inclou explícitament arxivats.
Un primer candidat per telèfon amb email incompatible impedeix aprofitar
altres candidats per aquell mateix telèfon en aquesta cerca.

En la creació estàndard, Odoo prepara el contacte a partir de les dades del
lead, inclosos el responsable, el telèfon, l’email i l’idioma si està assignat.
En reutilitzar un contacte, aquest mètode personalitzat no actualitza
explícitament el seu nom, email o idioma amb les dades de la petició.

## 12. Confirmació per correu

`action_send_email_confirmation()` requereix:

- `som_ff_send_lead_confirmation_email` activat a l’empresa de l’entorn.
- Contacte associat amb email.
- Remitent `som_ff_send_lead_confirmation_email_from` configurat.
- Plantilla de confirmació disponible.

Sense adjunts usa `som_email_template_lead_confirmation`. Amb adjunts usa
`som_email_template_lead_confirmation_invoice`, que anuncia la recepció
d’una factura i la preparació d’una comparativa.

Les plantilles tenen `partner_to=object.partner_id.id` i utilitzen
`object.partner_id.lang`. **El destinatari i l’idioma són els del contacte
associat**, que pot ser preexistent, no necessàriament els de l’entrada.

L’enviament es demana amb `force_send=True`, dins de l’execució de la petició.
Si l’equip comercial té àlies i domini, se’n construeix el `reply_to`.
El mètode intenta deixar un missatge de confirmació d’enviament al chatter.

Les precondicions incomplertes i les excepcions capturades pel mètode
retornen `False`. El controlador no inspecciona aquest retorn: **un `200`
no acredita l’enviament ni el lliurament del correu**.

## 13. Respostes i errors

### 13.1. Resposta correcta

La resposta usa HTTP `200`, no `201`:

```json
{
  "success": true,
  "message": "Lead successfully created",
  "lead_id": 123,
  "lead_name": "Contacte Exemple A",
  "lead_data": {
    "id": 123,
    "name": "Contacte Exemple A",
    "contact_name": "Contacte Exemple A",
    "email_from": "contacte.a@example.com",
    "phone": "+34000000001",
    "create_date": "2026-10-15T10:00:00"
  }
}
```

`create_date` es genera amb `isoformat()` sobre el datetime d’Odoo: UTC sense
sufix de zona horària. Si no hi ha data es retorna `null`.

Només s’afegeix `attachments` quan hi ha adjunts creats. No s’informa de
l’usuari assignat, l’activitat, el contacte, l’etapa ni del resultat del correu.
Les dades de resposta es preparen abans d’associar el contacte i d’enviar
la confirmació; no són una nova lectura final després de tots els passos.

### 13.2. Errors capturats pel controlador

| HTTP | Cas |
| --- | --- |
| `400` | JSON o UTF-8 invàlid |
| `400` | `ValidationError`, inclosa la impossibilitat de crear un contacte |
| `401` | Clau absent o incorrecta |
| `403` | `AccessError` |
| `500` | Altres excepcions capturades |

El JSON d’error conté `success=false`, `error` i `message`. En el cas genèric,
`message` inclou `str(e)`. Errors que es produeixin fora d’aquest bloc, per
exemple durant el flush final del framework, poden no seguir aquest format.

## 14. Transaccions, errors parcials i reintents

El controlador captura excepcions i retorna una resposta HTTP sense fer
rollback explícit ni delimitar l’operació amb un savepoint.

Al codi local d’Odoo 16, `odoo/http.py` delega el servei de la petició a
`service.model.retrying()`. A `odoo/service/model.py`, aquest mecanisme fa
flush i commit quan la funció retorna normalment; el codi d’estat HTTP
d’una resposta retornada no és, per si sol, una ordre de rollback.

Per tant, un error d’aplicació capturat que no deixi la transacció SQL
avortada pot produir aquest resultat:

```text
Es crea l’oportunitat
  → es crea el seguiment i eventualment els documents
  → assign_partner() llança ValidationError
  → el controlador retorna HTTP 400
  → poden persistir els registres ja creats
```

No s’ha reproduït aquest escenari en una prova HTTP durant l’estudi.
La conclusió deriva del flux del controlador i de la gestió transaccional
local. No s’ha d’estendre a tots els errors SQL: una transacció avortada o
un error posterior al controlador pot donar un resultat diferent.

Tampoc hi ha clau d’idempotència, identificador extern processat ni cerca
prèvia per reutilitzar una oportunitat. **Reenviar una petició pot crear
una altra oportunitat**, encara que es reutilitzi el mateix contacte.

La detecció personalitzada de possibles duplicats del model és informativa:
no constitueix un bloqueig d’entrada ni una fusió automàtica en aquest flux.

Els efectes externs, com un correu enviat immediatament, no es poden desfer
amb un rollback de la base de dades. Aquest fet també és rellevant per a
reintents després de timeouts o fallades tardanes.

## 15. Processos posteriors

Els processos següents no es criden des d’aquest endpoint, però poden actuar
sobre les oportunitats creades si estan activats o s’executen manualment.
Els crons de `data.xml` es defineixen inicialment inactius, amb interval d’una
hora i dins de `noupdate="1"`: l’estat efectiu s’ha de consultar a la base.

| Procés | Mètode | Efecte |
| --- | --- | --- |
| Associar contactes pendents | `_assign_partner_cron()` | Reintenta associar o crear contactes per a leads sense contacte |
| Planificar seguiment | `_create_upcoming_activities()` | Crea seguiment en registres amb responsable, sense cap activitat i fora de l’etapa guanyada seleccionada |
| Processar benvinguda | `_process_welcome_cron()` / `_process_welcome()` | Envia una plantilla, elimina activitats i canvia d’etapa |
| Buscar contractacions a l’ERP | `_erp_sync()` | Vincula la contractació i marca com a guanyada l’oportunitat |
| Comprovar inconsistències ERP | `_erp_sync_check_inconsistencies()` | Detecta vincles inconsistents |
| Corregir inconsistències ERP | `_erp_sync_fix_inconsistencies()` | Repara casos amb oportunitat local existent |

El seguiment posterior calcula el venciment amb
`stage_id.som_upcoming_activity_days`; no força avui com l’API inicial.

### 15.1. Benvinguda

El cron busca registres de `crm.stage_lead1` amb contacte i `email_from`,
fins al límit configurat en la crida, per defecte 50. No filtra explícitament
el sistema d’origen ni el tipus de registre.

Utilitza les plantilles CA/ES i l’etapa destí configurades a l’empresa.
L’elecció de plantilla es basa en l’idioma del lead; si no correspon usar
la plantilla ES disponible, utilitza la CA. Després de demanar l’enviament,
elimina **totes** les activitats del registre i el mou a l’etapa destí.

És un procés diferent de la confirmació immediata. Si està actiu, una entrada
sense documents pot arribar a rebre tots dos correus. Cal verificar que
l’etapa destí i les condicions evitin reenviaments no desitjats.

### 15.2. Sincronització amb l’ERP

La sincronització consulta `giscedata.crm.lead` mitjançant `erppeek`.
Busca contractacions finalitzades, amb pòlissa i encara no vinculades, dins
d’una finestra de dates de creació al voltant de la data actual, governada per
`som_crm_erp_contract_match_days` (10 dies per defecte, amb mínim 0).

Si el lead té CUPS, cerca per CUPS sense continuar amb altres estratègies.
Si no en té, prova successivament NIF, email i telèfon. Quan troba coincidència,
desa `som_erp_lead_id`, mou a l’etapa guanyada i activa el registre local;
després intenta escriure el vincle a l’ERP i recuperar el CUPS si falta.

L’API actual no assigna CUPS ni NIF des del JSON. Per tant, aquestes dades
només intervenen si s’han incorporat al model per una altra via.

## 16. Tests existents i verificació pendent

A `test_api_crm.py` hi ha casos de:

- Creació sense documents i amb document.
- Normalització de nom i email, etapa, canal i atribució UTM/MTM.
- Exclusió del responsable de l’equip i una activitat inicial en els casos
  de creació provats.
- Clau absent o incorrecta i JSON invàlid.
- Consulta de la documentació i registre del JSON/comentaris al chatter.

Són comprovacions presents al codi, **no resultats d’una execució en aquest
estudi**. També hi ha tests de lògica del model en fitxers separats; no s’ha
avaluat exhaustivament tota la cobertura del mòdul.

Casos rellevants a verificar per ampliar el contracte:

- Formats plans i amb `lead_data`, inclosa la ubicació dels fitxers.
- Tipus incorrectes, camps absents i contracte real de dades mínimes.
- Límits de mida, MIME i Base64.
- Persistència després d’un error tardà i rollback del flux complet.
- Reintents, peticions duplicades i concurrència amb identificadors externs.
- Contactes existents amb diferències de telèfon, email o idioma.
- Assignació sense candidats, exclusions, capacitat i absències.
- Creació d’activitat amb el flag desactivat i automatismes addicionals.
- Confirmació desactivada, errors d’enviament i interacció amb la benvinguda.

## 17. Configuració que cal verificar a la base de dades

El repositori no determina per si sol:

- El valor efectiu, la gestió i els consumidors de `som_crm.api_key`.
- Els idiomes actius i els noms/configuracions reals de les etapes.
- Els membres, empleats, exclusions i capacitats de l’equip comercial.
- Els flags d’activitats i correus, el remitent, els àlies i les plantilles.
- L’estat, usuari executor, codi i freqüència efectius dels crons.
- La configuració d’accés a l’ERP i la finestra temporal de cerca.
- Les accions automatitzades, altres extensions instal·lades i els límits
  del servidor/proxy que afectin aquesta ruta.

Aquestes comprovacions són necessàries per descriure el flux real de cada
entorn, especialment perquè bona part de les dades inicials són `noupdate`.

## 18. Implicacions i recomanacions per a la nova integració

Les propostes següents no formen part del comportament actual.

### 18.1. Concretar el contracte de negoci

Abans d’implementar cal obtenir un exemple de payload i concretar:

- Sistema d’origen i identificador únic de l’esdeveniment o lead extern.
- Dades mínimes, formats, idioma i camps nous que cal persistir.
- Significat dels adjunts, canal i etapa esperats.
- Política d’associació de contactes i de duplicats d’oportunitats.
- Assignació comercial i seguiment que s’han de generar.
- Correus que s’han d’enviar i participació en processos posteriors.
- Política de reintents i resposta esperada si la petició ja s’ha processat.

### 18.2. Preservar la compatibilitat

La recomanació inicial és preservar el contracte dels consumidors actuals
i fer explícites les regles de la nova entrada. Cal evitar que qualsevol
document genèric s’interpreti automàticament com una factura a simular.

Ampliar la mateixa ruta facilita la reutilització, però exigeix regles
clares de discriminació i compatibilitat. Una ruta específica permet un
contracte diferenciat, però requereix compartir la lògica de negoci per
evitar duplicar i fer divergir els fluxos. La decisió depèn del payload i
del resultat funcional acordat.

### 18.3. Separar contracte, negoci i efectes laterals

Convé validar estructura, tipus i requisits abans de crear registres;
delimitar l’operació perquè un error funcional no deixi una creació parcial;
i definir idempotència amb origen i identificador extern, inclosa la
concurrència. La deduplicació de contactes no substitueix la idempotència.

També cal decidir si l’enviament de correu ha de continuar sent immediat
o diferit: l’enviament immediat dona resposta ràpida al contacte, però
introdueix latència i un efecte extern que no es pot revertir amb la transacció.

### 18.4. Criteri de verificació de l’ampliació

La verificació ha de comprovar tant la resposta HTTP com els registres i
efectes generats: oportunitat, contacte, responsable, canal, etapa, activitats,
documents, atribució, chatter i correus. Els casos d’error i reintent han de
comprovar explícitament si hi ha persistència parcial o duplicacions.

## 19. Estat de l’estudi

- Anàlisi estàtica completada sobre el codi local disponible.
- Cap canvi funcional implementat com a part d’aquest document.
- Cap petició HTTP, test d’Odoo ni verificació de producció executats.
- Pendent: exemple de dades i requisits funcionals del nou sistema per
  definir l’abast de l’ampliació.
