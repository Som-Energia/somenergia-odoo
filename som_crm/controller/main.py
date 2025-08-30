# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError, AccessError
import werkzeug.wrappers

_logger = logging.getLogger(__name__)


class CRMLeadAPIController(http.Controller):
    
    def _authenticate_api_key(self, api_key):
        if not api_key:
            return False
        
        stored_api_key = request.env['ir.config_parameter'].sudo().get_param('som_crm.api_key')
        return api_key == stored_api_key
    
    # def _authenticate_user_session(self, login, password, database):
    #     try:
    #         uid = request.session.authenticate(database, login, password)
    #         return uid
    #     except Exception as e:
    #         _logger.error(f"Error en autenticación: {e}")
    #         return False
    
    def _validate_lead_data(self, data):
        required_fields = ['name']
        
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValidationError(f"Required field: {field}")
        
        # # Additional validation
        # if 'email' in data and data['email']:
        #     # Validación básica de email
        #     import re
        #     email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        #     if not re.match(email_pattern, data['email']):
        #         raise ValidationError("Invalid email format")
    
    def _prepare_lead_values(self, data):
        lead_values = {
            'name': data.get('name', 'New opportunity'),
            'contact_name': data.get('contact_name', data.get('name')),
            'email_from': data.get('email'),
            'phone': data.get('phone'),
            'description': data.get('description'),
            # 'mobile': data.get('mobile'),
            # 'website': data.get('website'),
            # 'street': data.get('street'),
            # 'street2': data.get('street2'),
            # 'city': data.get('city'),
            # 'zip': data.get('zip'),
            # 'referred': data.get('referred'),
        }
        
        # return not none values
        return {k: v for k, v in lead_values.items() if v is not None}
    
    @http.route('/api/crm/lead', type='http', auth='none', methods=['POST'], cors='*', csrf=False)
    def create_lead(self, **kwargs):
        """
        Sample:
        POST /api/crm/lead
        Headers: 
        - Content-Type: application/json
        - X-API-Key: tu_clave_secreta
        
        Body JSON:
        {
            "name": "Opportunity name",
            "contact_name": "Peter Samson",
            "email": "peter@company.com",
            "phone": "+34 123 456 789",
            "description": "Call me please"
        }
        """
        try:
            # Obtener datos JSON
            try:
                if hasattr(request, 'httprequest') and request.httprequest.data:
                    data = json.loads(request.httprequest.data.decode('utf-8'))
                else:
                    data = json.loads(request.params.get('data', '{}'))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                return self._json_response({
                    'success': False,
                    'error': 'JSON inválido',
                    'message': str(e)
                }, status=400)

            authenticated = False

            api_key = request.httprequest.headers.get('X-API-Key')
            if api_key and self._authenticate_api_key(api_key):
                authenticated = True
                _logger.info("Successful authentication via API Key")

            if not authenticated:
                return self._json_response({
                    'success': False,
                    'error': 'Authentication required',
                    'message': 'Provide X-API-Key in headers or auth in JSON body'
                }, status=401)
            
            # Data validation
            lead_data = data.get('lead_data', data)
            self._validate_lead_data(lead_data)
            
            # Prepare lead values
            lead_values = self._prepare_lead_values(lead_data)
            
            # Create lead
            odoo_bot = request.env.ref('base.user_root')
            lead = request.env['crm.lead'].with_user(odoo_bot).create(lead_values)

            _logger.info(f"Lead successfully created: ID {lead.id}, Name: {lead.name}")
            
            return self._json_response({
                'success': True,
                'message': 'Lead successfully created',
                'lead_id': lead.id,
                'lead_name': lead.name,
                'lead_data': {
                    'id': lead.id,
                    'name': lead.name,
                    'contact_name': lead.contact_name,
                    'email_from': lead.email_from,
                    'phone': lead.phone,
                    # 'stage': lead.stage_id.name if lead.stage_id else None,
                    # 'team': lead.team_id.name if lead.team_id else None,
                    # 'user': lead.user_id.name if lead.user_id else None,
                    'create_date': lead.create_date.isoformat() if lead.create_date else None
                }
            })
            
        except ValidationError as e:
            _logger.error(f"Validation error: {e}")
            return self._json_response({
                'success': False,
                'error': 'Validation error',
                'message': str(e)
            }, status=400)
            
        except AccessError as e:
            _logger.error(f"Access error: {e}")
            return self._json_response({
                'success': False,
                'error': 'Access error',
                'message': 'You do not have sufficient permissions.'
            }, status=403)
            
        except Exception as e:
            _logger.error(f"Error inesperado: {e}")
            return self._json_response({
                'success': False,
                'error': 'Internal server error',
                'message': str(e)
            }, status=500)

    def _json_response(self, data, status=200):
        response = werkzeug.wrappers.Response(
            response=json.dumps(data, ensure_ascii=False, indent=2),
            status=status,
            headers=[
                ('Content-Type', 'application/json; charset=utf-8'),
                ('Access-Control-Allow-Origin', '*'),
                ('Access-Control-Allow-Methods', 'POST, GET, OPTIONS'),
                ('Access-Control-Allow-Headers', 'Content-Type, X-API-Key'),
            ]
        )
        return response
