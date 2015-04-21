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

from openerp import models, fields, api, _
from openerp.exceptions import Warning

import logging
_logger = logging.getLogger('E-Invoice - Company')


class ResCompany(models.Model):

    _inherit = "res.company"

    e_invoice_ftp_path = fields.Char(string='FTP path for e-invoice')
    e_invoice_ftp_port = fields.Char(string='FTP port for e-invoice')
    e_invoice_ftp_username = fields.Char(string='Username')
    e_invoice_ftp_password = fields.Char(string='Password')
    e_invoice_ftp_filepath = fields.Char(string='FTP File path for e-invoice',
                                         help="/e-invoice/")
    sending_type = fields.Selection([('xml', 'XML'), ('pdf', 'PDF')],
                                    default='xml',
                                    string='Sending Type')

    @api.model
    def get_ftp_vals(self, company_id=False):
        # ----- If there isn't a company as parameter
        #       extracts it from user
        if not company_id:
            company_id = self.env.user.company_id.id
        company = self.browse(company_id)
        if not company.e_invoice_ftp_path:
            raise Warning(_('Define an FTP path for this company'))
        return (company.e_invoice_ftp_path,
                company.e_invoice_ftp_port or '21',
                company.e_invoice_ftp_username,
                company.e_invoice_ftp_password,
                company.e_invoice_ftp_filepath or '')

    @api.model
    def get_vat(self, company_id=False):
        # ----- If there isn't a company as parameter
        #       extracts it from user
        if not company_id:
            company_id = self.env.user.company_id.id
        company = self.browse(company_id)
        if not company.vat:
            _logger.info('No VAT for company %s' % (company.name))
        return company.vat or ''
