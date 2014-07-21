# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2014 Andrea Cometa All Rights Reserved.
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

from osv import fields, osv
from tools.translate import _


class account_invoice(osv.osv):
    _inherit = "account.invoice"

    _columns = {
        'nr_bollo': fields.char('Numero Bollo', size=10),
        'codice_commessa': fields.char('Codice Commessa', size=64),
        'codice_cup': fields.char('Codice CUP', size=64),
        'codice_cig': fields.char('Codice CIG', size=64),
        'history_ftpa': fields.text('Storico Trasmissione'),
        }

    def create(self, cr, uid, vals, context=None):
        if not vals:
            return super(account_invoice, self).create(cr, uid, vals, context)
        journal_id = vals.get('journal_id', False)
        partner_id = vals.get('partner_id', False)
        journal_obj = self.pool['account.journal']
        partner_obj = self.pool['res.partner']
        if journal_obj.browse(cr, uid, journal_id, context).e_invoice:
            partner = partner_obj.browse(cr, uid, partner_id, context)
            if not partner.ipa_code:
                raise osv.except_osv(
                    _('Error'),
                    _('Electronic Invoice but IPA code not found in partner'))
        return super(account_invoice, self).create(cr, uid, vals, context)


class account_journal(osv.osv):
    _inherit = "account.journal"

    _columns = {
        'e_invoice': fields.boolean(
            'Electronic Invoice',
            help="Check this box to determine that each entry of this journal\
 will be managed with Italian protocol for Electronical Invoice. Please use\
 the sequence like PA/xxxxxx"),
        'printing_module': fields.many2one(
            'ir.actions.report.xml', 'Printing Module',
            help="Printing module for e-invoice"),
    }

    _defaults = {
        'e_invoice': False,
    }
