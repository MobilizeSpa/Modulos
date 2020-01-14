# Copyright 2014-16 Akretion - Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2014 Serv. Tecnol. Avanzados - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round, float_compare

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    code = fields.Char('Código')

    @api.multi
    def write(self, vals):
        result = super(ProductTemplate, self).write(vals)
        if 'attribute_line_ids' in vals or 'code' in vals:
            for product_id in self.mapped('product_variant_ids'):
                attrs = sorted(product_id.mapped('attribute_value_ids'), key=lambda a:a.attribute_id.name, reverse=True)
                product_id.default_code = '%s-%s' % ( product_id.product_tmpl_id.code, '-'.join(attr.name for attr in attrs))
        return result
