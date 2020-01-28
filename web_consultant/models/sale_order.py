# Copyright 2014-16 Akretion - Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2014 Serv. Tecnol. Avanzados - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _

from odoo import api, fields, models, _

class SaleOrderLine(models.Model):
    _inherit = 'sale.order'
    _order = 'id,create_date DESC'

    @api.onchange('order_line')
    def _onchange_order_line_coupon(self):
        return self.recompute_coupon_lines()


