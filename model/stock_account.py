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

from openerp import models, fields, api, _


class StockInvoiceOnshipping(models.TransientModel):

    _inherit = 'stock.invoice.onshipping'

    def create_invoice(self, cr, uid, ids, context=None):
        res = super(StockInvoiceOnshipping, self).create_invoice(
            cr, uid, ids, context)
        invoice_obj = self.pool['account.invoice']
        for invoice_id in res:
            invoice = invoice_obj.browse(cr, uid, invoice_id, context)
            if not invoice.partner_id.ipa_code:
                continue
            pa_journal = self.pool['account.journal'].search(cr, uid,
                [('e_invoice', '=', True)])
            if not pa_journal:
                continue
            invoice_obj.write(
                cr, uid, invoice.id, {'journal_id': pa_journal[0]})
        return res
