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

class SaleOrderLine(models.Model):
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
        result = super(SaleOrderLine, self).write(vals)
        return result

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        """ Add or set product quantity, add_qty can be negative """
        self.ensure_one()
        product_context = dict(self.env.context)
        product_context.setdefault('lang', self.sudo().partner_id.lang)
        SaleOrderLineSudo = self.env['sale.order.line'].sudo().with_context(product_context)

        try:
            if add_qty:
                add_qty = float(add_qty)
        except ValueError:
            add_qty = 1
        try:
            if set_qty:
                set_qty = float(set_qty)
        except ValueError:
            set_qty = 0
        quantity = 0
        order_line = False
        if self.state != 'draft':
            request.session['sale_order_id'] = None
            raise UserError(_('It is forbidden to modify a sales order which is not in draft status.'))
        if line_id is not False:
            order_line = self._cart_find_product_line(product_id, line_id, **kwargs)[:1]

        # Create line if no line with product_id can be located
        if not order_line:
            # change lang to get correct name of attributes/values
            product = self.env['product.product'].with_context(product_context).browse(int(product_id))

            if not product:
                raise UserError(_("The given product does not exist therefore it cannot be added to cart."))

            no_variant_attribute_values = kwargs.get('no_variant_attribute_values') or []
            received_no_variant_values = product.env['product.template.attribute.value'].browse(
                [int(ptav['value']) for ptav in no_variant_attribute_values])
            received_combination = product.product_template_attribute_value_ids | received_no_variant_values
            product_template = product.product_tmpl_id

            # handle all cases where incorrect or incomplete data are received
            combination = product_template._get_closest_possible_combination(received_combination)

            # get or create (if dynamic) the correct variant
            product = product_template._create_product_variant(combination)

            if not product:
                raise UserError(_("The given combination does not exist therefore it cannot be added to cart."))

            product_id = product.id

            rw_product_id = (self.env['sale.order.line'].browse(line_id).product_id &
                             self.env['sale.coupon.program'].search([('discount_line_product_id', '=', product_id)]
                                                                    ).mapped('discount_line_product_id'))

            if rw_product_id:
                values = self.with_context(
                     rw_price_unit=order_line.price_unit)._website_product_id_change(self.id, product_id, qty=1)
            else:
                values = self.with_context()._website_product_id_change(self.id, product_id, qty=1)

            # add no_variant attributes that were not received
            for ptav in combination.filtered(lambda ptav: ptav.attribute_id.create_variant == 'no_variant' and ptav not in received_no_variant_values):
                no_variant_attribute_values.append({
                    'value': ptav.id,
                    'attribute_name': ptav.attribute_id.name,
                    'attribute_value_name': ptav.name,
                })

            # save no_variant attributes values
            if no_variant_attribute_values:
                values['product_no_variant_attribute_value_ids'] = [
                    (6, 0, [int(attribute['value']) for attribute in no_variant_attribute_values])
                ]

            # add is_custom attribute values that were not received
            custom_values = kwargs.get('product_custom_attribute_values') or []
            received_custom_values = product.env['product.attribute.value'].browse(
                [int(ptav['attribute_value_id']) for ptav in custom_values])

            for ptav in combination.filtered(
                    lambda ptav: ptav.is_custom and ptav.product_attribute_value_id not in received_custom_values):
                custom_values.append({
                    'attribute_value_id': ptav.product_attribute_value_id.id,
                    'attribute_value_name': ptav.name,
                    'custom_value': '',
                })

            # save is_custom attributes values
            if custom_values:
                values['product_custom_attribute_value_ids'] = [(0, 0, {
                    'attribute_value_id': custom_value['attribute_value_id'],
                    'custom_value': custom_value['custom_value']
                }) for custom_value in custom_values]

            # create the line
            order_line = SaleOrderLineSudo.create(values)
            # Generate the description with everything. This is done after
            # creating because the following related fields have to be set:
            # - product_no_variant_attribute_value_ids
            # - product_custom_attribute_value_ids
            order_line.name = order_line.get_sale_order_line_multiline_description_sale(product)

            try:
                order_line._compute_tax_id()
            except ValidationError as e:
                # The validation may occur in backend (eg: taxcloud) but should fail silently in frontend
                _logger.debug("ValidationError occurs during tax compute. %s" % (e))
            if add_qty:
                add_qty -= 1

        # compute new quantity
        if set_qty:
            quantity = set_qty
        elif add_qty is not None:
            quantity = order_line.product_uom_qty + (add_qty or 0)

        # Remove zero of negative lines
        if quantity <= 0:
            order_line.unlink()
        else:
            # update line
            no_variant_attributes_price_extra = [ptav.price_extra for ptav in
                                                 order_line.product_no_variant_attribute_value_ids]

            rw_product_id = (self.env['sale.order.line'].browse(line_id).product_id &
                             self.env['sale.coupon.program'].search([('discount_line_product_id', '=', product_id)]
                                                                    ).mapped('discount_line_product_id'))
            if rw_product_id:
                values = self.with_context(
                     no_variant_attributes_price_extra=no_variant_attributes_price_extra,
                     rw_price_unit=order_line.price_unit)._website_product_id_change(self.id,
                                                                                     product_id,
                                                                                     qty=quantity)
            else:
                values = self.with_context(
                    no_variant_attributes_price_extra=no_variant_attributes_price_extra)._website_product_id_change(
                    self.id,
                    product_id,
                    qty=quantity)
            if self.pricelist_id.discount_policy == 'with_discount' and not self.env.context.get('fixed_price'):
                order = self.sudo().browse(self.id)
                product_context.update({
                    'partner': order.partner_id,
                    'quantity': quantity,
                    'date': order.date_order,
                    'pricelist': order.pricelist_id.id,
                    'force_company': order.company_id.id,
                })
                product = self.env['product.product'].with_context(product_context).browse(product_id)
                if not rw_product_id:
                    values['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                        order_line._get_display_price(product),
                        order_line.product_id.taxes_id,
                        order_line.tax_id,
                        self.company_id
                    )
                else:
                    values['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                        values['price_unit'],
                        order_line.product_id.taxes_id,
                        order_line.tax_id,
                        self.company_id
                    )
            order_line.write(values)

            # link a product to the sales order
            if kwargs.get('linked_line_id'):
                linked_line = SaleOrderLineSudo.browse(kwargs['linked_line_id'])
                order_line.write({
                    'linked_line_id': linked_line.id,
                    'name': order_line.name + "\n" + _("Option for:") + ' ' + linked_line.product_id.display_name,
                })
                linked_line.write(
                    {"name": linked_line.name + "\n" + _("Option:") + ' ' + order_line.product_id.display_name})

        option_lines = self.order_line.filtered(lambda l: l.linked_line_id.id == order_line.id)
        for option_line_id in option_lines:
            self._cart_update(option_line_id.product_id.id, option_line_id.id, add_qty, set_qty, **kwargs)

        return {'line_id': order_line.id, 'quantity': quantity, 'option_ids': list(set(option_lines.ids))}

    @api.multi
    def _website_product_id_change(self, order_id, product_id, qty=0):
        order = self.sudo().browse(order_id)
        product_context = dict(self.env.context)
        product_context.setdefault('lang', order.partner_id.lang)
        product_context.update({
            'partner': order.partner_id,
            'quantity': qty,
            'date': order.date_order,
            'pricelist': order.pricelist_id.id,
            'force_company': order.company_id.id,
        })
        product = self.env['product.product'].with_context(product_context).browse(product_id)
        discount = 0

        if order.pricelist_id.discount_policy == 'without_discount':
            # This part is pretty much a copy-paste of the method '_onchange_discount' of
            # 'sale.order.line'.
            price, rule_id = order.pricelist_id.with_context(product_context).get_product_price_rule(product,
                                                                                                     qty or 1.0,
                                                                                                     order.partner_id)
            pu, currency = request.env['sale.order.line'].with_context(product_context)._get_real_price_currency(
                product, rule_id, qty, product.uom_id, order.pricelist_id.id)
            if pu != 0:
                if order.pricelist_id.currency_id != currency:
                    # we need new_list_price in the same currency as price, which is in the SO's pricelist's currency
                    date = order.date_order or fields.Date.today()
                    pu = currency._convert(pu, order.pricelist_id.currency_id, order.company_id, date)
                discount = (pu - price) / pu * 100
                if discount < 0:
                    # In case the discount is negative, we don't want to show it to the customer,
                    # but we still want to use the price defined on the pricelist
                    discount = 0
                    pu = price
        else:
            pu = product.price
            if order.pricelist_id and order.partner_id:
                order_line = order._cart_find_product_line(product.id)
                if order_line:
                    pu = self.env['account.tax']._fix_tax_included_price_company(pu, product.taxes_id,
                                                                                 order_line[0].tax_id, self.company_id)
        if self._context.get('rw_price_unit', 0):
            pu = self._context.get('rw_price_unit', 0)
        return {
            'product_id': product_id,
            'product_uom_qty': qty,
            'order_id': order_id,
            'product_uom': product.uom_id.id,
            'price_unit': pu,
            'discount': discount,
        }