# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Andre@ (<a.gallina@cgsoftware.it>)
#    All Rights Reserved
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


import logging
import os
from ftplib import FTP
import datetime

from openerp import models, fields, api, _
from openerp.report import render_report
from openerp.exceptions import Warning


_logger = logging.getLogger('Sending E-Invoice')


class WizardSendInvoice(models.TransientModel):

    _name = "wizard.send.invoice"
    _description = "Wizard For Sending E-Invoice"

    def create_report(self, res_ids, report_name=False, file_name=False,
                      data=False):
        if not report_name or not res_ids:
            return (
                False,
                Exception('Report name and Resources ids are required !!!'))
        try:
            ret_file_name = '/tmp/%s.pdf' % file_name
            (result, format) = render_report(
                self._cr, self._uid, res_ids, report_name, data)
            fp = open(ret_file_name, 'wb+')
            fp.write(result)
            fp.close()
        except Exception, e:
            print 'Exception in create report:', e
            return False, str(e)
        return True, ret_file_name

    def upload_file(self, ftp_vals, folder, file_name):
        try:
            ftp = FTP()
            ftp.connect(ftp_vals[0], int(ftp_vals[1]))
            ftp.login(ftp_vals[2], ftp_vals[3])
            try:
                ftp.cwd('%s%s' % (ftp_vals[4], folder))
                # move to the desired upload directory
                _logger.info('Currently in: %s', ftp.pwd())
                _logger.info('Uploading: %s', file_name)
                fullname = file_name
                name = os.path.split(fullname)[1]
                f = open(fullname, "rb")
                ftp.storbinary('STOR ' + name, f)
                f.close()
                _logger.info('Done!')
            finally:
                _logger.info('Close FTP Connection')
                ftp.quit()
        except:
            raise Warning(_('Error to FTP'))

    @api.multi
    def send_invoice(self):
        invoice_ids = self.env.context.get('active_ids', [])
        if not invoice_ids:
            raise Warning('No invoices to send')
        company_model = self.env['res.company']
        ftp_vals = company_model.get_ftp_vals()
        company = self.env.user.company_id
        # ---- Setting the folder where put pdf file
        folder = 'input flusso PDF'
        invoice_model = self.env['account.invoice']
        invoices = invoice_model.browse(invoice_ids)
        e_invoice_type = company.sending_type
        for invoice in invoices:
            if invoice.state in ('draft', 'sent'):
                raise Warning(
                    _('Invoice must be validated'))
            # ---- check if invoice can be send to SDI
            if not invoice.journal_id.e_invoice:
                raise Warning(
                    _('Is not E-Invoice check your Journal config!'))
            # ---- check if invoice can be send on FTP
            if invoice.einvoice_state not in ('draft', 'sent'):
                raise Warning(
                    _('Invoice has already been processed, \
                       you can not proceed to send!'))
            file_name = '%s%s' % (invoice.company_id.partner_id.vat,
                                  invoice.number.replace('/', '_'))
            if e_invoice_type == 'pdf':
                # ---- Standard for file name is:
                # ---- ITpartita_iva_mittente<...>.pdf
                report_name = (invoice.journal_id.printing_module.report_name or
                               False)
                report = self.create_report(invoice_ids, report_name,
                                            file_name, False)
                report_file = report[0] and [report[1]] or []
                if not report_file:
                    raise Warning(
                        _('PDF is not ready!'))
                self.upload_file(ftp_vals, folder, report_file[0])
            else:
                # ----- Send XML file
                xml_create = self.env['wizard.export.fatturapa'].with_context(
                    active_ids=[invoice.id, ]).exportFatturaPA()
                attach_id = xml_create.get('res_id', False)
                try:
                    data = self.env['fatturapa.attachment.out'].browse(
                        attach_id).ir_attachment_id.datas.decode('base64')
                    file = '/tmp/%s.xml' % file_name
                    fp = open(file, 'wb+')
                    fp.write(data)
                    fp.close()
                except Exception, e:
                    raise Warning(_('%s' % e))
                self.upload_file(ftp_vals, folder, file)
            # ----- Update history log
            history = invoice.history_ftpa or ''
            history = '%s\n' % history
            history = '%sFattura inviata in data %s' % (
                history, str(datetime.datetime.today()))
            invoice.history_ftpa = history
            invoice.einvoice_state = 'sent'

        return {'type': 'ir.actions.act_window_close'}
