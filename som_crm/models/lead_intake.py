# -*- coding: utf-8 -*-
"""Shared contact normalization, without choosing an intake workflow."""


def normalize_contact_data(data):
    name = data.get('contact_name', False)
    email = data.get('email', False)
    phone = data.get('phone', False)
    return {
        'contact_name': name.title() if name else name,
        'email_from': email.lower().strip() if email else email,
        'phone': phone.replace(' ', '') if phone else phone,
    }
