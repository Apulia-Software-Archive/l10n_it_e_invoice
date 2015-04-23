# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2015 Apulia Software All Rights Reserved.
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


class ResPartner(models.Model):

    _inherit = 'res.partner'

    def _commercial_fields(self, cr, uid, context=None):
        res = super(ResPartner, self)._commercial_fields(cr, uid, context)
        res.append('fiscalcode')
        return res
