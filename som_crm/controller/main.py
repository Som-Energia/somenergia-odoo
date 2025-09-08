# -*- coding: utf-8 -*-
import json
import logging
import base64
import mimetypes
from odoo import http, api,_
from odoo.http import request
from odoo.exceptions import ValidationError, AccessError
from odoo.tools.misc import get_lang
import werkzeug.wrappers

_logger = logging.getLogger(__name__)

FILE_MAX_SIZE_MB = 5
TOTAL_FILES_MAX_SIZE_MB = 20


class CRMLeadAPIController(http.Controller):

    def _authenticate_api_key(self, api_key):
        if not api_key:
            return False
        
        stored_api_key = request.env['ir.config_parameter'].sudo().get_param('som_crm.api_key')
        return api_key == stored_api_key
    
    def _validate_lead_data(self, data):
        # required_fields = ['contact_name', 'email', 'phone']
        required_fields = []
        
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValidationError(f"Required field: {field}")
        
        # # Additional validation
        # if 'email' in data and data['email']:
        #     # Basic mail format validation
        #     import re
        #     email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        #     if not re.match(email_pattern, data['email']):
        #         raise ValidationError("Invalid email format")
    
    def _prepare_lead_values(self, data):
        website_medium_id = request.env.ref('utm.utm_medium_website', raise_if_not_found=False) or False
        lang_code = data.get('lang', False)
        lang_id = get_lang(request.env, lang_code) if lang_code else False

        lead_values = {
            'name': data.get('name', _('Web form opportunity')),
            'contact_name': data.get('contact_name', data.get('name')),
            'email_from': data.get('email'),
            'phone': data.get('phone'),
            'description': data.get('description'),
            'medium_id': website_medium_id.id if website_medium_id else False,
            'lang_id': lang_id.id if lang_id else False,
            'type': 'opportunity',
            'user_id': False,
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


    def _get_json_data(self):
        if hasattr(request, 'httprequest') and request.httprequest.data:
            data = json.loads(request.httprequest.data.decode('utf-8'))
        else:
            data = json.loads(request.params.get('data', '{}'))

        # Extract files from JSON if exist
        files = data.pop('files', []) if isinstance(data.get('files'), list) else []

        return data, files

    def _validate_files(self, files):
        if not files:
            return

        # Allowed MIME types
        allowed_types = {
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp', 'image/webp',
            'application/pdf',
            'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'text/plain', 'text/csv',
            'application/zip', 'application/x-rar-compressed'
        }

        max_size = FILE_MAX_SIZE_MB * 1024 * 1024  # 5MB por archivo
        max_total_size = TOTAL_FILES_MAX_SIZE_MB * 1024 * 1024  # 20MB total

        total_size = 0

        for file_data in files:
            if not isinstance(file_data, dict):
                raise ValidationError("Invalid file format.")

            if 'filename' not in file_data or 'content' not in file_data:
                raise ValidationError("Each file must have “filename” and “content”.")

            filename = file_data['filename']
            if not filename or len(filename) > 255:
                raise ValidationError(f"Invalid file name: {filename}")

            try:
                content = base64.b64decode(file_data['content'])
                file_size = len(content)
            except Exception:
                raise ValidationError(f"Invalid file content in base64 for: {filename}")

            if file_size > max_size:
                raise ValidationError(f"File {filename} exceeds the maximum size of {FILE_MAX_SIZE_MB}MB")

            total_size += file_size

            # MIME type validation
            mime_type, _ = mimetypes.guess_type(filename)
            if file_data.get('mimetype'):
                mime_type = file_data['mimetype']

            if mime_type not in allowed_types:
                raise ValidationError(f"Tipo de archivo no permitido para {filename}: {mime_type}")

        if total_size > max_total_size:
            raise ValidationError(f"The total file size exceeds {TOTAL_FILES_MAX_SIZE_MB}MB.")

    def _create_lead_attachments(self, lead_id, files):
        if not files:
            return []

        attachments = []
        filename = ""

        for file_data in files:
            try:
                filename = file_data['filename']
                content = base64.b64decode(file_data['content'])

                mime_type = file_data.get('mimetype')
                if not mime_type:
                    mime_type, _ = mimetypes.guess_type(filename)
                    if not mime_type:
                        mime_type = 'application/octet-stream'

                attachment = request.env['ir.attachment'].sudo().create({
                    'name': filename,
                    'datas': base64.b64encode(content),
                    'mimetype': mime_type,
                    'res_model': 'crm.lead',
                    'res_id': lead_id.id,
                    'res_name': f"Lead Attachment - {filename}",
                    'type': 'binary',
                })

                attachments.append({
                    'id': attachment.id,
                    'name': attachment.name,
                    'mimetype': attachment.mimetype,
                    'file_size': attachment.file_size,
                })

                _logger.info(f"Created attachment: {filename} for lead {lead_id.id}")

            except Exception as e:
                _logger.error(f"Error creating attachment {filename}: {e}")
                raise ValidationError(f"Error processing file {filename}: {str(e)}")

        return attachments

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
            "contact_name": "Peter Samson",
            "email": "peter@company.com",
            "phone": "+34 123 456 789",
            "description": "Call me please",
            "lang": "es_ES" / "ca_ES" (code Español / Català)
            "files": [
                {
                    "filename": "document.pdf",
                    "content": "base64_encoded_content",
                    "mimetype": "application/pdf"
                }
            ]
        }
        """
        try:

            data, files = self._get_json_data()

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
            self._validate_files(files)
            
            # Prepare lead values
            lead_values = self._prepare_lead_values(lead_data)
            
            # Create lead
            odoo_bot = request.env.ref('base.user_root')
            lead_id = request.env['crm.lead'].with_user(odoo_bot).create(lead_values)

            # Create attachments
            attachments = []
            if files:
                attachments = self._create_lead_attachments(lead_id, files)

            _logger.info(
                f"Lead successfully created: ID {lead_id.id}, Name: {lead_id.name},  Attachments: {len(attachments)}"
            )
            
            response_data = {
                'success': True,
                'message': 'Lead successfully created',
                'lead_id': lead_id.id,
                'lead_name': lead_id.name,
                'lead_data': {
                    'id': lead_id.id,
                    'name': lead_id.name,
                    'contact_name': lead_id.contact_name,
                    'email_from': lead_id.email_from,
                    'phone': lead_id.phone,
                    # 'stage': lead.stage_id.name if lead.stage_id else None,
                    # 'team': lead.team_id.name if lead.team_id else None,
                    # 'user': lead.user_id.name if lead.user_id else None,
                    'create_date': lead_id.create_date.isoformat() if lead_id.create_date else None
                }
            }

            if attachments:
                response_data['attachments'] = attachments

            return self._json_response(response_data)

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return self._json_response({
                'success': False,
                'error': 'Invalid JSON',
                'message': str(e)
            }, status=400)

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

    @http.route('/api/crm/docs', type='http', auth='public', methods=['GET'],
                csrf=False, cors='*')
    def api_documentation(self, **kwargs):
        """
        Endpoint for API documentation
        """
        docs = {
            "api_info": {
                "title": "CRM Lead API",
                "version": "1.0.0",
                "description": "API REST to create CRM Leads in Odoo 16"
            },
            "authentication": {
                "methods": [
                    {
                        "type": "API Key",
                        "description": "Send API Key in header X-API-Key",
                        "example": "X-API-Key: your_secret_key_123"
                    },
                ]
            },
            "endpoints": [
                {
                    "path": "/api/crm/lead",
                    "method": "POST",
                    "description": "Create new CRM lead",
                    "headers": {
                        "Content-Type": "application/json",
                        "X-API-Key": "your_secret_key_123"
                    },
                    "request_body": {
                        "required_fields": [],
                        "optional_fields": [
                            "contact_name", "email", "phone", "description", "lang",
                        ],
                        "example": {
                            "contact_name": "Joana Pérez",
                            "email": "joana@empresa.com",
                            "phone": "+34 123 456 789",
                            "description": "Interesada en els vostres serveis",
                            "lang": "ca_ES",
                            "files": [
                                {
                                    "filename": "documento_test.pdf",
                                    "content": "base64_encoded_content",
                                    "mimetype": "application/pdf",
                                },
                            ],
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Lead successfully created",
                            "example": {
                                "success": True,
                                "message": "Lead successfully created",
                                "lead_id": 123,
                                "lead_name": "Web form opportunity"
                            }
                        },
                        "400": {
                            "description": "Validation error",
                            "example": {
                                "success": False,
                                "error": "Validation error",
                                "message": "Required field:"
                            }
                        },
                        "401": {
                            "description": "Unauthorized",
                            "example": {
                                "success": False,
                                "error": "Authentication required"
                            }
                        }
                    }
                },
            ],
            "testing": {
                "curl_examples": [
                    {
                        "description": "Create lead with API Key",
                        "command": 'curl -X POST "http://your-odoo.com/api/crm/lead" -H "Content-Type: application/json" -H "X-API-Key: your_key" -d \'{"contact_name": "Test contact name", "email": "test@example.com"}\''
                    },
                ]
            }
        }

        return self._json_response(docs)
