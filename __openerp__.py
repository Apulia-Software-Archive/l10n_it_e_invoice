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

{
    'name': "Electronic Invoice",
    'version': '0.1',
    'category': 'Account',
    'author': 'Apulia Software srl <info@apuliasoftware.it>',
    'website': 'www.apuliasoftware.it',
    'license': 'AGPL-3',
    "depends": [
        'account',
        'l10n_it_fatturapa',
        'l10n_it_fatturapa_out',
        'l10n_it_ipa',
        'stock_account',
        ],
    "data": [
        'security/security.xml',
        'security/ir.model.access.csv',
        'view/company_view.xml',
        'view/account_view.xml',
        'view/partner_view.xml',
        'view/attachment_view.xml',
        'wizard/send_invoice_view.xml',
        'report/account_report.xml',
        'data/e-invoice_data.xml',
        ],
    "active": False,
    "installable": True
}
