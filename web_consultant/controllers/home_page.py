from odoo import http
from odoo.addons.website.controllers.main import Website
from odoo.addons.sale.controllers.product_configurator import ProductConfiguratorController
from odoo import http
from odoo.addons.website.controllers.main import Website
from odoo.addons.sale.controllers.product_configurator import ProductConfiguratorController
from odoo.http import request
from odoo import fields, http, tools, _

# class Website(Website):
#
#     @http.route(auth='public')
#     def index(self, data={}, **kw):
#         super(Website, self).index(**kw)
#         return http.request.render('web_consultant.new_homepage', data)




class WebsiteSale(ProductConfiguratorController):

    @http.route('/cofdgggfde_sale', type='json', auth='user', website=True)
    def code_sale(self, access_token=None,page=0, category=None, search='', revive='',ppg=False, **post):
        order = request.website.sale_get_order()
        found = 1
        values = {}
        search = post.get('search_code', search)
        products = search != '' and request.env['product.product'].search([('default_code', '=', search)]) or request.env.get('product.product')
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
        products_in_order = products.filtered(lambda p: p & order.mapped('order_line.product_id'))
        products_not_in_order = products - products_in_order
        if not order:
            order = request.website.sale_get_order(force_create=True)
        for product in products_not_in_order:
            request.env['sale.order.line'].create({
                'product_id': product.id,
                'order_id': order.id,
                'name': product.name,
                'product_uom_qty': 1,
                'price_unit': 3,
            })
        for product in products_in_order:
            line = order.mapped('order_line').filtered(lambda l: l.product_id == product)
            line.product_uom_qty += 1
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
        values = {'code_sale_c': request.env['ir.ui.view'].sudo().render_template(
                                     "web_consultant.code_sale_c",
                                     values)}
        return values
        return request.render('web_consultant.code_sale_c', values)

    # if post.get('type') == 'popover':
    #     # force no-cache so IE11 doesn't cache this XHR
    #     return request.render("website_sale.cart_popover", values, headers={'Cache-Control': 'no-cache'})
    #
    # return request.render("website_sale.cart", values)

