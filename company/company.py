# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2014 Apulia Software All Rights Reserved.
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

from openerp.osv import osv, fields
from openerp.tools.translate import _

class res_company(osv.osv):

   _inherit = "res.company"
   
   _columns = {
        'e_invoice_ftp_path': fields.char('FTP path for e-invoice', size=128),
        'e_invoice_ftp_port': fields.char('FTP port for e-invoice', size=8),
        'e_invoice_ftp_username': fields.char('Username', size=64),
        'e_invoice_ftp_password': fields.char('Password', size=64),
        'e_invoice_ftp_filepath': fields.char('FTP File path for e-invoice',
                                              size=128,
                                              help='e-invoice/'),
   }

   def get_ftp_vals(self, cr, uid, company_id=False, context=None):
        # ----- If there isn't a company as parameter
        #       extracts it from user
        if not company_id:
            company_id = self.pool.get('res.users').browse(
                cr, uid, uid, context).company_id.id
        company = self.browse(cr, uid, company_id, context)
        if not company.e_invoice_ftp_path:
            raise osv.except_osv(
                _('Error'),
                _('Define an FTP path for this company'))
        return (company.e_invoice_ftp_path,
                company.e_invoice_ftp_port or '21',
                company.e_invoice_ftp_username,
                company.e_invoice_ftp_password,
                company.e_invoice_ftp_filepath or '')
