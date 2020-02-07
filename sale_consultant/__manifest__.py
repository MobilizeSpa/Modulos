# Copyright 2013 XCG Consulting (http://odoo.consulting)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Consultant Sales',
    'summary': 'Sales Managment for consultants functionality',
    'version': '1.0',
    'category': 'Sales',
    'author': 'Mobilize',
    'depends': ['web_consultant'],
    'data': [
        'views/res_partner.xml',
        'views/portal_templates.xml'
    ],
    'installable': True,
}
