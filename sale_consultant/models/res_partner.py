# Copyright 2014-16 Akretion - Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2014 Serv. Tecnol. Avanzados - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round, float_compare

class ResPartner(models.Model):
    _inherit = 'res.partner'

    auth_credit = fields.Float('Credito autorizado')
    available_credit = fields.Float('Credito disponible')
    used_credit = fields.Float('Credito utilizado')
    expired_debt = fields.Float('Deuda vencida')