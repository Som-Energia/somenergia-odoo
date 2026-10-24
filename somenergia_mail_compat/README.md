# SomEnergia Mail Compatibility

Aquest modul es un pont de compatibilitat temporal per al core OCB 16 fixat
del projecte.

Alguns addons de correu actualitzats utilitzen APIs que encara no existeixen
en aquesta revisio del core:

- `odoo.tools.email_split_and_format_normalize`
- `odoo.tools.mail.email_anonymize`

El modul incorpora backports condicionals d'aquestes APIs. No substitueix el
comportament existent: nomes les afegeix si el core encara no les proporciona.

## Deprecació i retirada

Aquest modul s'ha de retirar quan s'actualitzin els moduls de correu i el core
a revisions compatibles, de manera que cap addon requereixi APIs absents del
core OCB utilitzat. Abans d'eliminar-lo, cal verificar que les APIs ja estan
disponibles al core objectiu i executar la suite de tests de correu i Helpdesk.
