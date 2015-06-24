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

from openerp import models, fields, _, api
from ftplib import FTP
import os
import logging
import base64
from datetime import datetime
from xml.dom.minidom import parse
from openerp import tools

_logger = logging.getLogger('Sending E-Invoice')


class AccountInvoice(models.Model):

    _inherit = "account.invoice"

    _einvoice_state = [
        ('draft', 'Draft'),
        ('sent', 'Sent to FTP'),
        ('at', 'Avvenuta Trasmissione'),
        ('dt', 'Notifica Decorrenza Termini'),
        ('ec', 'Notifica Esito Cessionario Committente'),
        ('mc', 'Notifica Mancanza Consegna'),
        ('ne', 'Notifica Esito Cedente Prestatore'),
        ('ns', 'Notifica di Scarto'),
        ('rc', 'Ricevuta di Consegna'),
        ('se', 'Notifica di Scarto Esito Cessionario Commitente')]
    # fields definition

    history_ftpa = fields.Text(string='Storico Trasmissione', copy=False)
    sdi_file_name = fields.Char('Sdi File Name', size=128, copy=False)
    einvoice_state = fields.Selection(_einvoice_state,
                                      string='E-Invoice State',
                                      default='draft', copy=False)
    history_change = fields.One2many('einvoice.history', 'name',
                                     string='Historic Change', copy=False)

    @api.multi
    def onchange_partner_id(self, type, partner_id, date_invoice=False,
                            payment_term=False, partner_bank_id=False,
                            company_id=False):
        res = super(AccountInvoice, self).onchange_partner_id(
            type, partner_id, date_invoice, payment_term, partner_bank_id,
            company_id)
        if not res or not partner_id:
            return res
        if type not in ('out_invoice', 'out_refund'):
            return res
        partner = self.env['res.partner'].browse(partner_id)
        if not partner.ipa_code:
            return res
        pa_journal = self.env['account.journal'].search(
            [('e_invoice', '=', True)])
        if not pa_journal:
            return res
        res['value'].update({'journal_id': pa_journal[0].id})
        return res

    @api.model
    def create(self, vals):
        if not vals:
            return super(AccountInvoice, self).create(vals)
        journal_id = vals.get('journal_id', False)
        partner_id = vals.get('partner_id', False)
        if journal_id and partner_id and self.env['account.journal'].browse(
                journal_id).e_invoice:
            partner = self.env['res.partner'].browse(partner_id)
            if not partner.ipa_code:
                raise Warning(
                    'Electronic Invoice but IPA code not found in partner')
        return super(AccountInvoice, self).create(vals)

    def convert_timestamp(self, value):
        return datetime.fromtimestamp(
            int(value)/1e3).strftime('%Y-%m-%d %H:%M:%S')

    def read_xml_file(self, local_filename, invoice):
        parser = parse(local_filename)
        vals = {}
        file_data = open(local_filename, "rb").read()
        vals.update({'name': invoice.id, 'xml_content': file_data})
        for tags in parser.getElementsByTagName("esito"):
            for node in tags.getElementsByTagName("timestamp"):
                for value in node.childNodes:
                    date = self.convert_timestamp(value.data)
                    vals.update({
                        'date': date})
            for node in tags.getElementsByTagName("stato"):
                for value in node.childNodes:
                    vals.update({
                        'status_code': value.data})
            for node in tags.getElementsByTagName("msgErrore"):
                for value in node.childNodes:
                    vals.update({
                        'status_desc': value.data})
            for node in tags.getElementsByTagName("nomeFileSdi"):
                for value in node.childNodes:
                    note = "Nome file firmato: " + value.data
                    vals.update({
                        'note': note})
                    invoice.sdi_file_name = value.data
            for node in tags.getElementsByTagName("codStato"):
                for value in node.childNodes:
                    note = "Codice SDI: " + value.data
                    vals.update({
                        'note': note})
        for tags in parser.getElementsByTagName('DataOraRicezione'):
            for node in tags.childNodes:
                vals.update({'date': node.data[:19].replace('T', ' ')})
        for tags in parser.getElementsByTagName('ListaErrori'):
            errori = ""
            for node in tags.getElementsByTagName('Errore'):
                descrizione = 'N/A'
                if node.getElementsByTagName('Descrizione'):
                    descrizione = node.getElementsByTagName(
                        'Descrizione')[0].firstChild.data
                if node.getElementsByTagName('Codice'):
                    codice = node.getElementsByTagName(
                        'Codice')[0].firstChild.data
                    errori = '%s: %s\n%s' %(
                        codice, descrizione, errori)
            if errori:
                vals.update({'status_desc': errori,
                             'status_code': 'ERRORE!'})

        if 'date' not in vals:
            vals.update({'date': datetime.now().strftime('%Y-%m-%d')})

        tools.email_send(
            invoice.company_id.email,
            [invoice.company_id.email],
            'Controllo Fatture Elettroniche',
            'Fattura: %s - Messaggio %s' % (invoice.internal_number,
                                            vals.get('status_desc', '')),
            subtype='plain')

        return vals

    def check_output_xml_pa(self, ftp, ftp_vals, company_vat):
        # ----- Open the remote folder and read all the files
        folder = 'output XML-PA'
        ftp.cwd('%s%s' % (ftp_vals[4], folder))
        file_list = []
        ftp.retrlines('LIST', file_list.append)
        for filename in file_list:
            if not filename:
                _logger.info('No file found')
                continue
            tmp_filename = filename.split('#')[-1]
            if not tmp_filename.startswith(company_vat):
                continue
            # ----- Extracts invoice number from file name
            invoice_number = tmp_filename.split('.')[0].replace(
                company_vat, '').replace('_', '/')
            # ----- Search the invoice
            invoice_ids = self.search([('number', '=', invoice_number)])
            if not invoice_ids:
                _logger.info('No invoice found for number %s' % (
                    invoice_number))
                continue
            # ----- Create an attachment
            invoice = invoice_ids[0]
            if invoice.einvoice_state == 'at':
                _logger.info('invoice already processed %s' % (invoice.number))
                continue
            local_filename = os.path.join(r"/tmp/", filename)
            lf = open(local_filename, "wb")
            filename = filename.split(None, 8)[-1]
            ftp.retrbinary("RETR " + filename, lf.write, 8*1024)
            lf.close()
            attachment_data = {
                'name': '%s.xml.p7m' % invoice.internal_number,
                'type': 'binary',
                'datas_fname': '%s.xml.p7m' % invoice.internal_number,
                'datas': base64.encodestring(
                    open(local_filename, "rb").read()),
                'res_name': '%s.xml.p7m' % invoice.internal_number,
                'res_model': 'account.invoice',
                'res_id': invoice_ids[0],
                }
            self.env['ir.attachment'].create(attachment_data)

            invoice.einvoice_state = 'at'
            invoice.history_ftpa = '%s\nScaricata ed allegata versione \
firmata digitalmente della fattura XML PA in data \
%s' % (invoice.history_ftpa, str(datetime.today()))

        return False

    def check_edi_state_file(self, ftp, ftp_vals, company_vat):
        # ----- Open the remote folder and read all the files
        folder = 'output notifiche SdI'
        ftp.cwd('%s%s' % (ftp_vals[4], folder))
        file_list = []
        ftp.retrlines('LIST', file_list.append)
        for filename in file_list:
            filename = filename.split(None, 8)[-1]
            if not filename:
                _logger.info('No file found')
                continue
            if not filename.startswith(company_vat):
                continue
            filename_value = filename.split('_')
            # ----- Search the invoice
            invoice_ids = self.search(
                [('sdi_file_name', '=', filename_value[1])])
            if not invoice_ids:
                _logger.info('No invoice found for number %s' % (
                    filename_value[1]))
                continue
            # ----- Extract datas from XML file
            local_filename = os.path.join(r"/tmp/", filename)
            lf = open(local_filename, "wb")
            ftp.retrbinary("RETR " + filename, lf.write, 8*1024)
            lf.close()
            vals = self.read_xml_file(local_filename, invoice_ids[0])
            # ----- Move file in backup folder
            ftp.rename(
                filename, ftp_vals[4] + '/elaborati/' + filename)
            # ----- Write historic change
            self.env['einvoice.history'].create(vals)
        return True

    def check_xml_state_file(self, ftp, ftp_vals, company_vat):
        # ----- Open the remote folder and read all the files
        folder = 'Stati delle fatture'
        ftp.cwd('%s%s' % (ftp_vals[4], folder))
        file_list = []
        ftp.retrlines('LIST', file_list.append)
        for filename in file_list:
            filename = filename.split(None, 8)[-1]
            if not filename:
                _logger.info('No file found')
                continue
            if not filename.startswith(company_vat):
                codice = filename.split('_')
                if not codice[1]:
                    continue
                stringa = '%s%s%s' %('%', codice[1], '%')
                invoice_ids = self.search(
                    [('sdi_file_name', 'ilike', stringa)])
                if invoice_ids:
                    local_filename = os.path.join(r"/tmp/", filename)
                    lf = open(local_filename, "wb")
                    ftp.retrbinary("RETR " + filename, lf.write, 8*1024)
                    lf.close()
                    vals = self.read_xml_file(local_filename, invoice_ids[0])
                    # ----- Move file in backup folder
                    ftp.rename(
                        filename, ftp_vals[4] + '/elaborati/' + filename)
                    # ----- Write historic change
                    self.env['einvoice.history'].create(vals)
                continue
            invoice_number = filename.split('.')[0][13:].replace('_', '/')
            # ----- Search the invoice
            invoice_ids = self.search([('number', '=', invoice_number)])
            if not invoice_ids:
                _logger.info('No invoice found for number %s' % (
                    invoice_number))
                continue
            # ----- Extract datas from XML file
            local_filename = os.path.join(r"/tmp/", filename)
            lf = open(local_filename, "wb")
            ftp.retrbinary("RETR " + filename, lf.write, 8*1024)
            lf.close()
            vals = self.read_xml_file(local_filename, invoice_ids[0])
            # ----- Move file in backup folder
            ftp.rename(
                filename, ftp_vals[4] + '/elaborati/' + filename)
            # ----- Write historic change
            self.env['einvoice.history'].create(vals)
        return True

    @api.multi
    def force_check_einvoice_status(self):
        return self.check_einvoice_status()

    def check_einvoice_status(self):
        company_obj = self.env['res.company']
        company_vat= self.env.user.company_id.vat
        # company_vat = company_obj.get_vat(cr, uid, False, context)
        ftp_vals = company_obj.get_ftp_vals()
        try:
            ftp = FTP()
            ftp.connect(ftp_vals[0], int(ftp_vals[1]))
            ftp.login(ftp_vals[2], ftp_vals[3])
            # ----- Loop all the folders on ftp server and check files
            self.check_output_xml_pa(ftp, ftp_vals, company_vat)

            self.check_edi_state_file(ftp, ftp_vals, company_vat)

            self.check_xml_state_file(ftp, ftp_vals, company_vat)

            _logger.info('Close FTP Connection')

            ftp.quit()
        except:
            raise Warning('Error to FTP')

    @api.multi
    def finalize_invoice_move_lines(self, move_lines):
        # manage of split_payment
        move_lines = super(AccountInvoice, self).finalize_invoice_move_lines(move_lines)
        # modify some data in move lines
        if self.type == 'out_invoice' or self.type == 'out_refund':
            journal = self.journal_id
            # ----- Check if fiscal positon is active for intra CEE invoice
            if not journal:
                return move_lines
            if not journal.e_invoice:
                return move_lines
            amount_vat = self.amount_tax
            cli_account_id = self.partner_id.property_account_receivable.id
            new_line = {
                'name': '/',
                'debit': 0.0,
                'partner_id': self.partner_id.id,
                'account_id': cli_account_id}
            reconcile = self.env['account.move.reconcile'].create(
                {'type': 'manual'})
            if reconcile:
                new_line.update({'reconcile_partial_id': reconcile.id})
            if self.type == 'out_invoice':
                new_line.update({'credit': amount_vat})
            if self.type == 'out_refund':
                new_line.update({'debit': amount_vat})
            vat_line = {}
            for line in move_lines:
                if ('credit' in line[2]  and abs(line[2]['credit'] - amount_vat) < 0.00001 and self.type == 'out_invoice') or ('debit' in line[2]  and abs(line[2]['debit'] - amount_vat) < 0.00001 and self.type == 'out_refund'):
                    vat_line = {
                        'name': 'IVA - Split Payment',
                        'account_id': line[2]['account_id'],
                    }
                    if self.type == 'out_invoice':
                        vat_line.update({'debit': amount_vat})
                    if self.type == 'out_refund':
                        vat_line.update({'credit': amount_vat})
                    break
            for line in move_lines:
                if line[2]['account_id'] == cli_account_id:
                    line[2].update({'reconcile_partial_id': reconcile.id})
                    break
            move_lines.append((0, 0, new_line))
            move_lines.append((0, 0, vat_line))
        return move_lines


class AccountJournal(models.Model):

    _inherit = "account.journal"

    #fields
    e_invoice = fields.Boolean(
        string='Electronic Invoice',
    help="Check this box to determine that each entry of this journal\
will be managed with Italian protocol for Electronical Invoice. Please use\
the sequence like PA/xxxxxx", default=False)

    printing_module = fields.Many2one('ir.actions.report.xml',
                                      string='Printing Module',
                                      help="Printing module for e-invoice")


class EinvoiceHistory(models.Model):

    _name = "einvoice.history"
    _order = 'date'

    name = fields.Many2one('account.invoice', required=True,
                           ondelete='cascade')
    date = fields.Datetime(string='Date Action', required=True)
    note = fields.Text()
    status_code = fields.Char(size=25)
    status_desc = fields.Text()
    xml_content = fields.Text()
