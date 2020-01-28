# Copyright 2013 XCG Consulting (http://odoo.consulting)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Consultant Web',
    'summary': 'E-commerce Web Site Modification for consultants functionality',
    'version': '1.0',
    'category': 'Website',
    'author': 'Mobilize',
    'depends': ['web', 'website_sale', 'website_sale_coupon'],
    'data': [
        'views/code_sale.xml',
        'views/home_page.xml',
        'data/code_sale.xml',
        'views/product_template_views.xml'
    ],
    'installable': True,
}
