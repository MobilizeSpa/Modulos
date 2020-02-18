from odoo import http
from odoo.addons.website.controllers.main import Website
from odoo.addons.sale.controllers.product_configurator import ProductConfiguratorController
from odoo.http import request
from odoo import fields, http, tools, _
import json

class WebsiteSale(ProductConfiguratorController):

    @http.route('/code_sale', type='http', auth='user', website=True)
    def code_sale(self, access_token=None,page=0, category=None, search='', qty=0,revive='',ppg=False, **post):
        order = request.website.sale_get_order()
        found = 1
        values = {}
        if post.get('search_code', False):
            search = ''
        products = search != '' and request.env['product.product'].search([('default_code', 'ilike', search)])[:1] or request.env.get('product.product')
        products = products.filtered(lambda p: p.default_code.upper() == search.upper())
        if order and order.state != 'draft':
            request.session['sale_order_id'] = None
            order = request.website.sale_get_order()
        values = {}
        if access_token:
            abandoned_order = request.env['sale.order'].sudo().search([('access_token', '=', access_token)],
                                                                      limit=1)
            if not abandoned_order:  # wrong token (or SO has been deleted)
                return request.render('website.404')
            if abandoned_order.state != 'draft':  # abandoned cart already finished
                values.update({'abandoned_proceed': True})
            elif revive == 'squash' or (revive == 'merge' and not request.session[
                'sale_order_id']):  # restore old cart or merge with unexistant
                request.session['sale_order_id'] = abandoned_order.id
                return request.redirect('/shop/cart')
            elif revive == 'merge':
                abandoned_order.order_line.write({'order_id': request.session['sale_order_id']})
                abandoned_order.action_cancel()
            elif abandoned_order.id != request.session[
                'sale_order_id']:  # abandoned cart found, user have to choose what to do
                values.update({'access_token': abandoned_order.access_token})

        if order:
            from_currency = order.company_id.currency_id
            to_currency = order.pricelist_id.currency_id
            compute_currency = lambda price: from_currency._convert(
                price, to_currency, request.env.user.company_id, fields.Date.today())
        else:
            compute_currency = lambda price: price
        if post.get('product_id_cons', False):
            products_in_order = products.browse([int(post.get('product_id_cons'))])
        else:
            products_in_order = products.filtered(lambda p: p & order.mapped('order_line.product_id'))
        products_not_in_order = products - products_in_order
        if not order:
            order = request.website.sale_get_order(force_create=True)
        for product in products_not_in_order:
            request.env['sale.order.line'].sudo().create({
                'product_id': product.id,
                'order_id': order.id,
                'name': product.name,
                'product_uom_qty': qty,
                'price_unit': product.list_price,
            })
        for product in products_in_order:
            line = order.mapped('order_line').filtered(lambda l: l.product_id == product)
            if(int(post.get('quantity_product_id',0))):
                line.product_uom_qty = int(post.get('quantity_product_id',1))
            elif qty:
                line.product_uom_qty += int(qty)
        values.update({
            'website_sale_order': order,
            'compute_currency': compute_currency,
            'date': fields.Date.today(),
            'suggested_products': [],
            'products': products,
        })
        if order:
            _order = order
            if not request.env.context.get('pricelist'):
                _order = order.with_context(pricelist=order.pricelist_id.id)
            values['suggested_products'] = _order._cart_accessories()
        if not products and search != '':
            found = 0
        values.update({'found': found,})
        if post.get('line_id_cons', False):
            line = order.mapped('order_line').filtered(lambda l: l.id == int(post.get('line_id_cons', False)))
            programs = order.authomatic_valid_program_p(line[:1].product_id,
                                                              line[:1].product_uom_qty,
                                                              line[:1].price_unit)
            if programs:
                line_rwrd = order.mapped('order_line').filtered(lambda l: l.product_id in programs.mapped('reward_product_id'))
                line_rwrd.unlink()
            line.unlink()
        if order:
            order.recompute_coupon_lines()
        return request.render('web_consultant.code_sale_c', values)

    @http.route([
        '''/shop''',
        '''/shop/page/<int:page>''',
        '''/shop/category/<model("product.public.category", "[('website_id', 'in', (False, current_website_id))]"):category>''',
        '''/shop/category/<model("product.public.category", "[('website_id', 'in', (False, current_website_id))]"):category>/page/<int:page>'''
    ], type='http', auth="user", website=True)
    def shop(self, page=0, category=None, search='', ppg=False, **post):
        return super(WebsiteSale, self).shop(page, category, search, post)

    @http.route(['/shop/payment'], type='http', auth="public", website=True, sitemap=False)
    def payment(self, **post):
        """ Payment step. This page proposes several payment means based on available
        payment.acquirer. State at this point :

         - a draft sales order with lines; otherwise, clean context / session and
           back to the shop
         - no transaction in context / session, or only a draft one, if the customer
           did go to a payment.acquirer website but closed the tab without
           paying / canceling
        """
        order = request.website.sale_get_order()
        for line_id in order.mapped('order_line'):
                product_id = line_id.product_id
                program_ids = request.env['sale.coupon.program'].search([
                    ('discount_line_product_id', '=', product_id.id)
                ])
                product_sale_program_ids = (line_id.order_id.mapped('order_line.product_id') &
                                            program_ids.mapped('reward_product_id'))
                if product_sale_program_ids:
                    price_unit = line_id.order_id.mapped('order_line').filtered(
                        lambda l: l.product_id == product_sale_program_ids[:1]).price_unit
                    # price_unit = (line_id.mapped('order_id.order_line.product_id') & product_sale_program_ids[:1]).price_unit
                    line_id.write({'price_unit': - price_unit})
        return super(WebsiteSale, self).payment()

    @http.route(['/shop/cart'], type='http', auth="public", website=True)
    def cart(self, **post):
        order = request.website.sale_get_order()
        self.find_program(order)
        return super(WebsiteSale, self).cart(**post)


    def find_program(self, order):
        if order.order_line:
            order_lines = order.order_line
            for line in order_lines:
                program_ids = order.authomatic_valid_program_p(line.product_id,
                                                              line.product_uom_qty,
                                                              line.price_unit)
                if program_ids and not any(line.website_change for line in order.mapped('order_line')):
                    if not any(line.product_id == program_ids.reward_product_id for line in order.mapped('order_line')):
                        for program_id in program_ids:
                            line.website_change = True
                            line.sudo().create(
                                {
                                    'product_uom_qty': program_id.reward_product_quantity,
                                    'price_unit': program_id.reward_product_id.lst_price,
                                    'product_id': program_id.reward_product_id.id,
                                    'name': program_id.reward_product_id.name,
                                    'product_uom': program_id.reward_product_id.uom_id.id,
                                    'order_id':order.id,
                                }
                            )