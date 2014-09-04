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


from osv import osv
from tools.translate import _
import logging
import netsvc
import os
from ftplib import FTP
import datetime


_logger = logging.getLogger('Sending E-Invoice')


class wizard_send_invoice(osv.osv_memory):

    _name = "wizard.send.invoice"
    _description = "Wizard For Sening E-Invoice"

    def create_report(self, cr, uid, res_ids,
                      report_name=False, file_name=False,
                      data=False, context=False):
        if not report_name or not res_ids:
            return (
                False,
                Exception('Report name and Resources ids are required !!!'))
        try:
            ret_file_name = '/tmp/'+file_name+'.pdf'
            service = netsvc.LocalService("report."+report_name)
            (result, format) = service.create(cr, uid, res_ids, data, context)
            fp = open(ret_file_name, 'wb+')
            fp.write(result)
            fp.close()
        except Exception, e:
            print 'Exception in create report:', e
            return (False, str(e))
        return (True, ret_file_name)

    def upload_file(self, cr, uid, ftp_vals, folder, file_name, context):
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
            raise osv.except_osv('Error', 'Error to FTP')

    def send_invoice(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        company_obj = self.pool.get('res.company')
        ftp_vals = company_obj.get_ftp_vals(cr, uid, False, context)

        # ---- Setting the folder where put pdf file
        folder = 'input flusso PDF'

        # ---- Select the printing module to print and create PDF
        invoice_ids = context.get('active_ids', [])
        invoice_obj = self.pool.get('account.invoice')
        invoice = invoice_obj.browse(cr, uid, invoice_ids, context)[0]
        report_name = invoice.journal_id.printing_module.report_name or False

        # ---- check if invoice can be send to SDI
        if not invoice.journal_id.e_invoice:
            raise osv.except_osv(
                _('Error'),
                _('Is not E-Invoice check your Journal config!'))
        if invoice.einvoice_state not in ('draft', 'sent'):
            raise osv.except_osv(
                _('Error!'),
                _('invoice has already been processed, \
                   you can not proceed to send!'))

        # ---- Standard for file name is:
        # ---- ITpartita_iva_mittente<...>.pdf
        file_name = invoice.company_id.partner_id.vat
        #~ file_name += '<' + invoice.number.replace('/', '_') + '>'
        file_name += invoice.number.replace('/', '_')

        report = self.create_report(
            cr, uid, invoice_ids, report_name, file_name, False, context)
        report_file = report[0] and [report[1]] or []
        if not report_file:
            raise osv.except_osv(
                _('Error'),
                _('PDF is not ready!'))
        self.upload_file(
            cr, uid, ftp_vals, folder, report_file[0], context)
        history = invoice.history_ftpa or ''
        history = '%s\n' % (history)
        history = "%sFattura inviata in data %s" % (
            history, str(datetime.datetime.today()))
        invoice_obj.write(
            cr, uid, invoice_ids[0],
            {'history_ftpa': history, 'einvoice_state': 'sent'}, context)

        return {'type': 'ir.actions.act_window_close'}
