# SomEnergia Mail Compatibility

Aquest modul es un pont de compatibilitat temporal per al core OCB 16 fixat
del projecte.

Alguns addons de correu actualitzats utilitzen APIs que encara no existeixen
en aquesta revisio del core:

- `odoo.tools.email_split_and_format_normalize`
- `odoo.tools.mail.email_anonymize`

El mòdul incorpora backports condicionals d'aquestes APIs: només les afegeix
si el core encara no les proporciona.

## Missatges automàtics (`auto_comment`)

A partir de `16.0.1.1.0`, també incorpora el comportament `auto_comment` del
correu d'Odoo 16, necessari per als tipus de missatge previstos per Helpdesk
Workbench. No modifica el core ni els addons externs.

- Afegeix el tipus a `mail.message` i al compositor si el core no el defineix.
- Les plantilles de seguiment automàtic utilitzen aquest tipus per defecte;
  es respecta qualsevol `message_type` indicat explícitament. Com al core
  oficial, el compositor en mode `mass_mail` continua generant `email`.
- Les respostes entrants a aquests missatges es tracten com a converses,
  encara que la plantilla original utilitzi un subtipus intern. Les respostes
  a notes internes ordinàries continuen sent internes.
- El chatter identifica aquests missatges com a automàtics.

A diferència dels dos helpers, aquest backport sí que canvia el comportament
del correu automàtic de tots els models amb seguiment. No converteix missatges
històrics ni canvia les regles d'accés. Helpdesk pot filtrar aquests missatges
i excloure'ls del trasllat de comunicacions durant una fusió de tickets.

La implementació pren com a referència `addons/mail` de la branca oficial
`16.0` d'Odoo i el canvi original
[`39f14ca`](https://github.com/odoo/odoo/commit/39f14ca2c92a617bd387d5a29d69479f90d92a44).
El despatx de plantilles reprodueix el del core fixat amb el nou valor per
defecte, per incloure també les plantilles aportades per altres addons.
Quan el core ja defineix `auto_comment`, els canvis de seguiment i de parsing
deleguen en el comportament natiu.

Cal actualitzar aquest addon després de desplegar el canvi. En desinstal·lar-lo
sobre el core antic, els missatges `auto_comment` es conserven com a
`notification`; no s'eliminen. Aquesta conversió no és reversible
automàticament i no converteix el subtipus intern en públic.

## Validació

Els tests cobreixen les plantilles, el compositor, les respostes entrants,
la privacitat de les notes internes i la delegació al core natiu. La prova
QUnit del chatter requereix Chrome i `websocket-client` a l'entorn de tests;
aquesta dependència no és necessària en producció.

## Deprecació i retirada

Aquest modul s'ha de retirar quan s'actualitzin els moduls de correu i el core
a revisions compatibles, de manera que cap addon requereixi APIs absents del
core OCB utilitzat. Abans d'eliminar-lo, cal verificar que les dues APIs i el
comportament complet d'`auto_comment` ja estan disponibles al core objectiu,
actualitzar el mòdul contra aquest core i executar la suite de tests de correu
i Helpdesk. Cal revisar també el client web i la propietat de les opcions de
selecció abans de desinstal·lar el pont.
