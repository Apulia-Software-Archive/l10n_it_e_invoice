# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2015 Andrea Cometa All Rights Reserved.
#                       www.andreacometa.it
#                       openerp@andreacometa.it
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


class WizardExportFatturapa(models.TransientModel):

    _inherit = "wizard.export.fatturapa"

    def exportFatturaPA(self, cr, uid, ids, context=None):
        invoice_obj = self.pool['account.invoice']
        invoice_ids = context.get('active_ids', False)

        for invoice in invoice_obj.browse(cr, uid, invoice_ids, context):
            if not invoice.fatturapa_attachment_out_id:
                continue
            notes = 'Effettuato Nuovo Invio della fattura %s in data %s' % (
                invoice.internal_number, fields.Date.today())
            self.pool['fatturapa.attachment.out'].write(
                cr, uid, invoice.fatturapa_attachment_out_id.id,
                {'fatturapa_notes': notes}, context)
            invoice_obj.write(
                cr, uid, invoice.id,
                {'fatturapa_attachment_out_id': False}, context)
        return super(WizardExportFatturapa, self).exportFatturaPA(
            cr, uid, ids, context)
