# Copyright 2014-16 Akretion - Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2014 Serv. Tecnol. Avanzados - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _

from odoo import api, fields, models, _
from odoo.tools.safe_eval import safe_eval
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    _order = 'id,create_date DESC'



    @api.model
    def authomatic_valid_program_p(self, product_id, product_uom_qty, price_unit):
        programs = self.env['sale.coupon.program'].search([
            ('reward_type', '=', 'product'),
            ('rule_products_domain', '!=', False),
            ('reward_product_id', '!=', False),
            '|', ('rule_min_quantity', '<=', product_uom_qty),
            ('rule_minimum_amount', '=', price_unit),
            ('promo_code_usage', 'in',(False,'no_code_needed')),
        ])
        now = datetime.now()
        date_programs = self.env['sale.coupon.program']
        for program in programs:
            if not program.rule_date_from and not program.rule_date_to:
                date_programs |= program
            if program.rule_date_from and program.rule_date_to and now > program.rule_date_from and now < program.rule_date_to:
                date_programs |= program
            if not program.rule_date_to and (program.rule_date_from and now > program.rule_date_from):
                date_programs |= program
            if not program.rule_date_from and (program.rule_date_to and now < program.rule_date_to):
                date_programs |= program
        programs = date_programs
        program_ids = self.env['sale.coupon.program']
        if isinstance(product_id, int):
            product_id = self.env['product.product'].browse(product_id)
        for program_id in programs:
            domain = safe_eval(program_id.rule_products_domain)
            if (product_id.search(domain) & product_id):
                program_ids |= program_id
        return program_ids
        
    @api.model
    def create(self, vals):
        order_lines = vals.get('order_line', False)
        if order_lines:
            for line in order_lines:
                    line = line[2]
                    product_id = self.env['product.product'].browse(line.get('product_id', False))
                    program_ids = self.authomatic_valid_program_p(product_id,
                                                                  line.get('product_uom_qty', 1),
                                                                  line.get('price_unit', 0))
                    if program_ids:
                        for program_id in program_ids:
                            vals['order_line'].append((0, 0, {
                                'product_uom_qty': program_id.reward_product_quantity,
                                'price_unit': program_id.reward_product_id.lst_price,
                                'product_id': program_id.reward_product_id.id,
                                'name': program_id.reward_product_id.name,
                                'product_uom': program_id.reward_product_id.uom_id.id,
                            }))
                            vals['order_line'].append((0, 0, {
                                'product_uom_qty': program_id.reward_product_quantity,
                                'price_unit': - program_id.reward_product_id.lst_price,
                                'product_id': program_id.discount_line_product_id.id,
                                'name': program_id.reward_product_id.name,
                                'product_uom': program_id.reward_product_id.uom_id.id,
                            }))
        order_ids = super(SaleOrderLine, self).create(vals)
        order_ids.recompute_coupon_lines()
        return order_ids

    @api.multi
    def write(self, vals):
        order_line_list = vals.get('order_line', False)
        if order_line_list:
            #TODO: falta valorar los many
            update_create_line_ids = list(filter(lambda l: l[0] in (0, 1), order_line_list))
            unlink_line_ids = list(filter(lambda l: l[0] in (2, 3,), order_line_list))
            product_ids = {}
            for up_create_line in update_create_line_ids:
                if up_create_line[0] == 1:
                    product_id = up_create_line[1]
                    product_ids.setdefault(product_id, {})
                    product_ids[product_id].update(
                                                    {'product_uom_qty': up_create_line[2].get('product_uom_qty', 1)}
                                                   )
                    product_ids[product_id].update({'price_unit': up_create_line[2].get('price_unit', 0)})
                if up_create_line[0] == 0:
                    product_id = up_create_line[2].get('product_id', False)
                    if product_id:
                        product_ids.setdefault(product_id, {})
                        product_ids[product_id].update(
                                                {'product_uom_qty': up_create_line[2].get('product_uom_qty', 1)}
                                                       )
                        product_ids[product_id].update(
                            {'price_unit': up_create_line[2].get('price_unit', 0)}
                        )
            for k, v in product_ids.items():
                product_id = self.env['product.product'].browse(k)
                program_ids = self.authomatic_valid_program_p(product_id, v['product_uom_qty'], v['price_unit'])
                if program_ids:
                    for program_id in program_ids:
                        vals['order_line'].append((0, 0, {
                            'product_uom_qty': program_id.reward_product_quantity,
                            'price_unit': program_id.reward_product_id.lst_price,
                            'product_id': program_id.reward_product_id.id,
                            'name': program_id.reward_product_id.name,
                            'product_uom': program_id.reward_product_id.uom_id.id,
                        }))
                        if program_id.promo_code_usage == 'no_code_needed' or program_id.program_type == 'coupon_program':
                            vals['order_line'].append((0, 0, {
                                'product_uom_qty': program_id.reward_product_quantity,
                                'price_unit': - program_id.reward_product_id.lst_price,
                                'product_id': program_id.discount_line_product_id.id,
                                'name': program_id.reward_product_id.name,
                                'product_uom': program_id.reward_product_id.uom_id.id,
                                'is_reward_line': True
                            }))
        result = super(SaleOrder, self).write(vals)
        return result

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        if line_id and product_id and set_qty == 0 and not add_qty:
            self.ensure_one()
            line = self.env['sale.order.line'].browse(line_id)
            programs = self.authomatic_valid_program_p(
                                                        product_id,
                                                        line.product_uom_qty,
                                                        line.price_unit)
            if programs:
                line_rwrd = self.mapped('order_line').filtered(
                    lambda l: l.product_id in programs.mapped('reward_product_id'))
                line_rwrd.unlink()
        res = super(SaleOrder, self)._cart_update(product_id=product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty, **kwargs)
        return res


