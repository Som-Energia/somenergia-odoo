# API d’entrada de leads de col·laboradors

Implementació local de la proposta de la [issue #126](https://github.com/Som-Energia/somenergia-odoo/issues/126),
per a Odoo 16 Community. Complementa l’[estudi del canal web](analisi-api-entrada-leads.md).
El contracte per compartir i importar a Swagger/Insomnia és
[`crm_partner_lead_api.json`](crm_partner_lead_api.json).

L’abast actual és una única empresa d’Odoo amb diversos col·laboradors externs.
Cada col·laborador té la seva integració, clau i regles d’assignació; no hi ha
selecció ni segregació multiempresa pròpia d’aquest canal.

## Activació

1. Actualitzar `som_crm` perquè es carreguin els camps, models, permisos i vistes
   nous. La versió passa de `0.1` a `16.0.1.0.0`. El canvi és additiu: no cal
   transformar les oportunitats existents, que no tindran identitat externa.
2. A **CRM → Configuració → Integracions de col·laboradors** (el nom es pot
   mostrar en anglès segons les traduccions), crear una integració amb nom,
   codi únic, equip, etapa inicial no guanyada i comercials.
3. Com a administrador, prémer **Generate / rotate API key**. Copiar la clau
   de la notificació: es mostra una sola vegada i no es desa en clar.
4. Habilitar la integració (`enabled`).
5. Habilitar **Allow collaborator lead intake** als ajustos CRM.

Les integracions i l’interruptor global estan desactivats per defecte.
Desactivar una integració o arxivar-la bloqueja només aquell col·laborador;
desactivar l’interruptor global bloqueja totes les integracions d’aquest canal.
La ruta i la clau web `som_crm.api_key` són independents.

L’interruptor es desa al paràmetre global `som_crm.collaborator_intake_enabled`,
no a `res.company`. Si el paràmetre no existeix, el canal està desactivat.
Les oportunitats conserven el camp estàndard d’empresa d’Odoo i es creen amb
l’empresa per defecte de l’usuari tècnic del servidor, sense heretar el context
d’una sessió del navegador.

Els responsables CRM poden gestionar la configuració. Només administració
pot generar claus i accedir als camps de credencials; els comercials poden
llegir les integracions, sense credencials.

La clau té un selector aleatori i un secret d’alta entropia. Només es desa
un resum SHA-256 del token complet i es compara en temps constant. Regenerar
la clau invalida l’anterior. El col·laborador es dedueix exclusivament de la clau.

## Validació amb Pydantic

El contracte de dades es defineix a
[`CollaboratorLeadPayload`](../pydantic/lead_models.py), amb Pydantic v2
(`pydantic>=2.7,<3`, declarat al manifest i als requirements del mòdul).
La versió `2.7.1` dels requirements generals de l’entorn és compatible.

L’esquema aplica tipus estrictes, rebuig de camps desconeguts, longituds,
normalització i la regla d’email o telèfon. `_validate_payload()` n’adapta
els errors a `LeadIntakeError` amb HTTP `400`, sense retornar les dades rebudes,
el context intern de Pydantic ni els noms de camps desconeguts.

La validació de format d’email conserva `odoo.tools.email_normalize`, sense
canviar a `EmailStr`. Els idiomes actius, permisos i configuració es comproven
al servei d’Odoo; la unicitat continua protegida per la base de dades.

`model_dump()` inclou tots els camps opcionals amb `''` quan no s’envien.
Les normalitzacions i el diccionari resultant preserven el contingut utilitzat
per calcular l’empremta d’idempotència anterior a aquesta refactorització.

## Contracte

```http
POST /api/crm/partner/lead
Content-Type: application/json
X-API-Key: <clau de la integració>
```

És una API servidor a servidor, sense sessió requerida ni CORS obert.
El client ha d’enviar `Content-Length`; el cos màxim és de **64 KiB**.
No s’admeten JSON-RPC, l’embolcall `lead_data`, adjunts ni camps addicionals.

```json
{
  "id_external_lead": "REF-000123",
  "contact_name": "Contacte Exemple A",
  "email": "contacte.a@example.com",
  "phone": "+34 000 000 001",
  "lang": "ca_ES",
  "comments": "Contacte derivat per valorar una oferta."
}
```

Exemple fictici. El telèfon és il·lustratiu, no un número de contacte vàlid.

| Camp | Obligatori | Regles |
| --- | --- | --- |
| `id_external_lead` | Sí | Text no buit, màxim 128 caràcters; conserva zeros inicials i distingeix majúscules |
| `contact_name` | Sí | Text no buit, màxim 255; es normalitza amb `.title()` |
| `email` | Email o telèfon | Màxim 254; minúscules, espais extrems eliminats i validació de format Odoo |
| `phone` | Email o telèfon | Màxim 64; elimina espais simples; no valida una numeració internacional completa |
| `lang` | No | `ca_ES` o `es_ES`, que ha d’estar actiu a Odoo; ometre o buit per no seleccionar idioma |
| `cups` | No | Màxim 64 abans de normalitzar; elimina blancs i passa a majúscules; format final de 20 o 22 caràcters |
| `comments` | No | Màxim 10.000; nota interna amb contingut escapat |

Tots els camps presents han de ser cadenes, no `null`, números o llistes.
Els camps opcionals omesos i les cadenes buides equivalen a absència.
S’eliminen espais dels extrems de les cadenes. Els identificadors externs
són sensibles a majúscules/minúscules després d’aquesta normalització.

El format admès del CUPS és `ES` + 16 dígits + 2 lletres, amb un sufix opcional
d’un dígit i una lletra. Es valida l’estructura, **no les lletres de control**.
Es desa al camp ja existent `som_cups`.

## Resultat i reintents

Creació nova: HTTP `201`.

```json
{
  "success": true,
  "created": true,
  "lead_id": 123,
  "id_external_lead": "REF-000123"
}
```

La identitat és la parella **integració + ID extern**. Dos col·laboradors
poden usar el mateix ID. La restricció SQL també inclou registres arxivats.

- Repetició amb les mateixes dades normalitzades: `200`, mateix `lead_id`,
  `created=false`, sense repetir activitats, contacte ni assignació.
- Mateix ID amb dades normalitzades diferents: `409`; no actualitza el lead.
- Les modificacions manuals posteriors al lead no afecten aquesta comparació:
  es conserva una empremta del contingut original normalitzat.

El contracte és de creació, no d’actualització. No s’ha de reciclar l’ID per
representar una altra derivació. Eliminar físicament una oportunitat elimina
també la reserva de la seva identitat; arxivar-la la conserva.

Odoo 16 usa `REPEATABLE READ`. Si dues peticions competeixen pel mateix ID,
la que perd la restricció d’unicitat demana una fallada SQL `40001` perquè
el framework reintenti la transacció completa amb una fotografia nova.
El cos HTTP queda en memòria cau de Werkzeug per poder repetir la lectura.
No es fan commits intermedis.

## Errors

```json
{
  "success": false,
  "error": "external_id_conflict",
  "message": "This external ID has different data."
}
```

| HTTP | Significat |
| --- | --- |
| `400` | JSON, camps, tipus, dades mínimes, idioma o CUPS invàlids |
| `401` | Credencial absent o incorrecta; es comprova abans de llegir el cos |
| `403` | Integració desactivada o arxivada |
| `409` | ID extern existent amb un contingut diferent |
| `411` | Falta `Content-Length` |
| `413` | Cos superior a 64 KiB |
| `415` | Content-Type diferent d’`application/json` |
| `422` | Configuració o permisos insuficients per completar el flux |
| `500` | Error inesperat, sense exposar-ne els detalls interns |
| `503` | Canal de col·laboradors desactivat globalment |

Els errors SQL que es propaguen al framework (per exemple, reintents SQL
exhaurits) poden rebre el format d’error propi d’Odoo. Davant d’un timeout o
fallada transitòria, el client pot repetir el mateix ID i el mateix contingut.
Els errors de validació o els conflictes requereixen revisar la petició.

## Flux comercial

1. Validar clau, interruptors i dades.
2. Comprovar idempotència.
3. Dins d’un savepoint, crear una oportunitat amb canal **Collaborators**,
   integració, ID extern, equip i etapa configurats.
4. Seleccionar un comercial exclusivament del conjunt configurat.
5. Reutilitzar `assign_partner()` per buscar o crear el contacte amb els
   mateixos criteris de coincidència que el canal web.
6. Crear una activitat per avui si està habilitada i hi ha responsable.
7. Registrar una còpia JSON del payload acceptat al chatter, juntament amb
   integració i ID extern; els comentaris també es publiquen com a nota separada.

Si falla un pas necessari es desfà l’operació local sencera. El JSON registrat
és el cos original acceptat (abans de normalitzar-lo), sense headers HTTP ni
la clau `X-API-Key`; el contingut es mostra escapat dins d’un `<pre>`. El payload
pot incloure dades personals perquè és el mateix contracte que s’ha rebut.
Les peticions no vàlides i els reintents idèntics no creen missatges nous.

La selecció comercial reutilitza el criteri de capacitat i les exclusions
temporals. En aquest canal només es consideren absències aprovades. Els usuaris
han de ser interns, actius, usuaris CRM, membres o responsables de
l’equip i tenir empleat associat per superar el criteri de presència compartit.

En desar la integració es valida estrictament que els comercials configurats
pertanyen a l’equip i són usuaris interns de CRM. Si més endavant un comercial
és desactivat, perd el grup CRM o deixa de pertànyer a l’equip, s’exclou del
conjunt elegible durant la recepció; la petició no falla si encara hi ha altres
candidats vàlids. Si no en queda cap, el lead es crea sense responsable ni activitat.

Si hi ha candidats amb capacitat, se n’escull un aleatòriament. Si tots estan
plens, se’n pot assignar un igualment. Sense candidats elegibles, queda sense
responsable i sense activitat: no s’assigna ningú de fora del conjunt configurat.

Desactivar la creació d’activitat a la integració també impedeix que el cron
de seguiment la creï després per aquestes oportunitats.

## Correus i altres automatismes

No es criden les confirmacions des de l’endpoint. Els mètodes de confirmació
i benvinguda, incloses les accions massives i el cron, exclouen les oportunitats
que tenen integració d’origen. Es mantenen les notificacions internes d’Odoo
i els correus manuals deliberats.

La relació d’origen és persistent i immutable, independentment del canal o
l’etapa visibles. Copiar una oportunitat no copia la identitat externa.
No es pot eliminar una integració referenciada per oportunitats.

La sincronització ERP existent no canvia: pot utilitzar el CUPS rebut.
Cal revisar els automatismes particulars de cada base de dades que enviïn
correus per altres vies.

## Verificació a càrrec de l’operador

Els tests nous tenen els tags `som_crm_partner_intake` (models) i
`som_crm_partner_api` (HTTP). També cal executar la regressió existent del web,
equips i benvinguda:

```text
--test-tags "som_crm_partner_intake,som_crm_partner_api,som_test_crm_lead_api_http,som_crm_team,som_welcome_email"
```

La comanda completa d’Odoo i la configuració de l’entorn es documenten a
la [skill de tests del repositori](../../.agents/skills/odoo-test/SKILL.md).

Els tests HTTP comproven els reintents seqüencials i els conflictes d’ID, però
no envien peticions simultànies; per tant, no són una prova de concurrència real.

La implementació es lliura sense executar els tests ni actualitzar cap base
de dades; aquestes comprovacions les farà l’usuari.
