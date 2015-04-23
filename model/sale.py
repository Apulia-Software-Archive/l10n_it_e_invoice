# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2051 Apulia Software All Rights Reserved.
#                       www.apuliasoftware.it
#                       info@apuliasoftware.it
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, _, api


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    @api.model
    def _prepare_invoice(self, order, lines):

        invoice_vals = super(SaleOrder, self)._prepare_invoice(order, lines)
        if not order:
            return invoice_vals
        if not order.partner_invoice_id.ipa_code:
            return invoice_vals
        pa_journal = self.env['account.journal'].search(
            [('e_invoice', '=', True)])
        if not pa_journal:
            return  invoice_vals
        invoice_vals.update({'journal_id': pa_journal[0].id})
        return invoice_vals
