import logging

from odoo.api import Environment, SUPERUSER_ID


_logger = logging.getLogger(__name__)


OLD_PROJECT_END_DATE = '2026-06-10'
NEW_PROJECT_START_DATE = '2026-06-13'
NEW_PROJECT_MANAGER_ID = 281
NEW_AREA_PROJECT_NAMES = [
    'Trobades ET',
    'Descans',
    'Trobades estratègiques equips',
    'Formació transversal',
    'Formació específica',
    'Sòcia de treball',
    'Atenció',
    "Gestió de l'atenció",
    'Operativa comer',
    'Operativa comer empresa',
    'Fraus i anomalies',
    'Reclamació deute pendent',
    'Coordinació comer',
    'Canvis normatius comer',
    'Aprovisionament',
    'Acció comercial B2B',
    'Acció comercial B2C',
    'Estratègia comercial',
    'Producte tarifes',
    'Anàlisi barrera 100€',
    'Venda creuada Soms',
    'Flux solar',
    'Descompte social',
    'Som Energia Activa',
    'Actualització preus',
    'Flexibilitat de la demanada',
    'Hibridació de plantes',
    'Gurb promoció',
    'Gurb explotació',
    'Representació',
    'Generation kWh',
    'Auvi',
    'Som Comunitats',
    "Xarxa d'instal.ladores",
    'Coordinadora CE',
    'Gestió de plantes de tercers',
    'CAEs',
    'Prospecció noves iniciatives',
    'Treball amb CR',
    'Pilotatge de la coope',
    'Pla estratègic',
    'Gestió de plantes pròpies',
    'Creació noves plantes',
    'Compliment jurídic',
    'Jurídic comercialització',
    'Jurídic generació',
    'Jurídic cooperativisme',
    'Marketing',
    'Producte',
    'Gestió oficina',
    'Gestió laboral',
    'Entorn laboral',
    'Comptabilitat',
    'Manteniment sistemes',
    'Gestió de servidors propis',
    'Helpdesk',
    'Web',
    'Oficina Virtual',
    'Odoo laboral',
    'Indicadors',
    'ERP',
    'Gestió IT',
    'Esc[hola]',
    'Assemblea General',
    'Gran Conversa',
    'Trobada Sòcies Activistes',
    'Parcicipació sòcies',
    'Formació a les sòcies',
    'Lobby',
    'Representació intercoop',
    'Difusió',
]


def _close_legacy_projects(env, area_tag, transversal_tag, excluded_project):
    Project = env['project.project']
    domain = [
        ('name', 'not in', NEW_AREA_PROJECT_NAMES),
        '|',
            ('date_start', '=', False),
            ('date_start', '<=', OLD_PROJECT_END_DATE),
        '|',
            ('tag_ids', 'in', area_tag.ids),
            ('tag_ids', 'in', transversal_tag.ids),
    ]
    if excluded_project:
        domain.append(('id', '!=', excluded_project.id))
    legacy_projects = Project.search(domain)
    _logger.info("Closing %s legacy area/transversal projects", len(legacy_projects))
    if legacy_projects:
        legacy_projects.write({'date': OLD_PROJECT_END_DATE})


def _create_or_align_new_area_projects(env, area_tag, transversal_tag):
    Project = env['project.project']
    existing_projects = Project.search([('name', 'in', NEW_AREA_PROJECT_NAMES)])
    existing_by_name = {project.name: project for project in existing_projects}

    to_create = []
    for name in NEW_AREA_PROJECT_NAMES:
        project = existing_by_name.get(name)
        if project:
            commands = []
            if transversal_tag in project.tag_ids:
                commands.append((3, transversal_tag.id))
            if area_tag not in project.tag_ids:
                commands.append((4, area_tag.id))
            vals = {
                'date_start': NEW_PROJECT_START_DATE,
                'date': False,
                'allow_timesheets': True,
                'user_id': NEW_PROJECT_MANAGER_ID,
            }
            if commands:
                vals['tag_ids'] = commands
            project.write(vals)
            continue

        to_create.append({
            'name': name,
            'allow_timesheets': True,
            'date_start': NEW_PROJECT_START_DATE,
            'user_id': NEW_PROJECT_MANAGER_ID,
            'tag_ids': [(6, 0, [area_tag.id])],
        })

    if to_create:
        _logger.info("Creating %s new area projects", len(to_create))
        Project.create(to_create)


def migrate(cr, version):
    env = Environment(cr, SUPERUSER_ID, {})
    area_tag = env.ref('somenergia_custom.som_project_tag_area')
    transversal_tag = env.ref('somenergia_custom.som_project_tag_transversal_project')
    excluded_project = env.ref('somenergia_custom.som_cumulative_hours_project', raise_if_not_found=False)

    _logger.info("Applying project validity rollout migration 16.0.1.1.0")
    _close_legacy_projects(env, area_tag, transversal_tag, excluded_project)
    _create_or_align_new_area_projects(env, area_tag, transversal_tag)
    _logger.info("Project validity rollout migration finished")
