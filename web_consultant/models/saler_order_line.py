# Copyright 2014-16 Akretion - Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2014 Serv. Tecnol. Avanzados - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    _order = 'id,create_date DESC'
    
    @api.multi
    def write(self, vals):
        product_id = vals.get('product_id', False)
        product_uom_qty = vals.get('product_uom_qty', False)
        price_unit = vals.get('price_unit', False)
        order_id = vals.get('order_id', False)
        if product_id and order_id and product_uom_qty:
            program_ids = self.env['sale.order'].authomatic_valid_program_p(
                product_id,
                product_uom_qty,
                price_unit
            )
            product_ids = self.env['sale.order'].browse(order_id).mapped('order_line.product_id').ids
            if program_ids:
                for program_id in program_ids:
                    if not any(product_id == program_id.reward_product_id.id for product_id in product_ids):
                        self.create({
                            'product_uom_qty': program_id.reward_product_quantity,
                            'price_unit': - program_id.reward_product_id.lst_price,
                            'product_id': program_id.discount_line_product_id.id,
                            'name': program_id.reward_product_id.name,
                            'product_uom': program_id.reward_product_id.uom_id.id,
                            'order_id': order_id,
                        })
                        self.create({
                            'product_uom_qty': program_id.reward_product_quantity,
                            'price_unit': program_id.reward_product_id.lst_price,
                            'product_id': program_id.reward_product_id.id,
                            'name': program_id.reward_product_id.name,
                            'product_uom': program_id.reward_product_id.uom_id.id,
                            'order_id': order_id
                        })

        return super(SaleOrderLine, self).write(vals)