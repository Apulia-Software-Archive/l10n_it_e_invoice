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
from ftplib import FTP
import os
import logging
import base64
from datetime import datetime
from xml.dom.minidom import parse
from openerp import tools

_logger = logging.getLogger('Sending E-Invoice')


class account_invoice(osv.osv):
    _inherit = "account.invoice"

    _columns = {
        'nr_bollo': fields.char('Numero Bollo', size=10),
        'codice_commessa': fields.char('Codice Commessa', size=64),
        'codice_cup': fields.char('Codice CUP', size=64),
        'codice_cig': fields.char('Codice CIG', size=64),
        'history_ftpa': fields.text('Storico Trasmissione'),
        'sdi_file_name': fields.char('Sdi File Name', size=128),
        'einvoice_state': fields.selection(
            (('draft', 'Draft'),
             ('sent', 'Sent to FTP'),
             ('at', 'Avvenuta Trasmissione'),
             ('dt', 'Notifica Decorrenza Termini'),
             ('ec', 'Notifica Esito Cessionario Committente'),
             ('mc', 'Notifica Mancanza Consegna'),
             ('ne', 'Notifica Esito Cedente Prestatore'),
             ('ns', 'Notifica di Scarto'),
             ('rc', 'Ricevuta di Consegna'),
             ('se', 'Notifica di Scarto Esito Cessionario Commitente'),
             ), 'E-Invoice State'),
        'history_change': fields.one2many(
            'einvoice.history', 'name', 'Historic Change'),
        }
    _defaults = {
        'einvoice_state': 'draft',
        }

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default = dict(default, history_change=[], einvoice_state='draft',
                       history_ftpa='', sdi_file_name='')
        return super(account_invoice, self).copy(
            cr, uid, id, default=default, context=context)

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

    def convert_timestamp(self, value):
        return datetime.fromtimestamp(
            int(value)/1e3).strftime('%Y-%m-%d %H:%M:%S')

    def read_xml_file(self, cr, uid, local_filename, invoice_id, context=None):
        parser = parse(local_filename)
        vals = {}
        file_data = open(local_filename, "rb").read()
        vals.update({'name': invoice_id, 'xml_content': file_data})
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
                    self.pool.get('account.invoice').write(
                        cr, uid, [invoice_id],
                        {'sdi_file_name': value.data}, context)
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

        if not 'date' in vals:
            vals.update({'date': datetime.now().strftime('%Y-%m-%d')})

        invoice = self.browse(cr, uid, invoice_id, context)
        tools.email_send(
            invoice.company_id.email,
            [invoice.company_id.email],
            'Controllo Fatture Elettroniche',
            'Fattura: %s - Messaggio %s' %(invoice.internal_number,
                                           vals.get('status_desc', '')),
            subtype='plain',
            cr=cr)

        return vals

    def check_output_xml_pa(self, cr, uid, ftp, ftp_vals, company_vat,
                            context=None):
        # ----- Open the remote folder and read all the files
        folder = 'output XML-PA'
        ir_attachment = self.pool.get('ir.attachment')
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
            invoice_ids = self.search(
                cr, uid, [('number', '=', invoice_number)])
            if not invoice_ids:
                _logger.info('No invoice found for number %s' % (
                    invoice_number))
                continue
            # ----- Create an attachment
            invoice = self.browse(cr, uid, invoice_ids[0], context)
            if invoice.einvoice_state == 'at':
                _logger.info('invoice already processed %s' % (invoice.number))
                continue
            local_filename = os.path.join(r"/tmp/", filename)
            lf = open(local_filename, "wb")
            filename = filename.split(None, 8)[-1]
            ftp.retrbinary("RETR " + filename, lf.write, 8*1024)
            lf.close()
            attachment_data = {
                'name': filename,
                'type': 'binary',
                'datas_fname': filename,
                'datas': base64.encodestring(
                    open(local_filename, "rb").read()),
                'res_name': filename,
                'res_model': 'account.invoice',
                'res_id': invoice_ids[0],
                }
            ir_attachment.create(cr, uid, attachment_data,
                                 context=context)

            vals = {'einvoice_state': 'at',
                    'history_ftpa': '%s\nScaricata ed allegata versione \
firmata digitalmente della fattura XML PA in data \
%s' % (invoice.history_ftpa, str(datetime.today()))}
            self.write(cr, uid, [invoice_ids[0]], vals, context)
        return False

    def check_edi_state_file(self, cr, uid, ftp, ftp_vals, company_vat,
                             context=None):
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
            filename_value = filename.split('_')
            # ----- Search the invoice
            invoice_ids = self.search(
                cr, uid, [('sdi_file_name', 'ilike', filename_value[1])])
            if not invoice_ids:
                _logger.info('No invoice found for number %s' % (
                    filename_value[1]))
                continue
            # ----- Extract datas from XML file
            local_filename = os.path.join(r"/tmp/", filename)
            lf = open(local_filename, "wb")
            ftp.retrbinary("RETR " + filename, lf.write, 8*1024)
            lf.close()
            vals = self.read_xml_file(
                cr, uid, local_filename, invoice_ids[0], context)
            # ----- Move file in backup folder
            ftp.rename(
                filename, ftp_vals[4] + '/elaborati/' + filename)
            # ----- Write historic change
            self.pool.get('einvoice.history').create(cr, uid, vals, context)
        return True

    def check_xml_state_file(self, cr, uid, ftp, ftp_vals, company_vat,
                             context=None):
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
                    cr, uid,
                    [('sdi_file_name', 'ilike', stringa)])
                if invoice_ids:
                    local_filename = os.path.join(r"/tmp/", filename)
                    lf = open(local_filename, "wb")
                    ftp.retrbinary("RETR " + filename, lf.write, 8*1024)
                    lf.close()
                    vals = self.read_xml_file(
                        cr, uid, local_filename, invoice_ids[0], context)
                    # ----- Move file in backup folder
                    ftp.rename(
                        filename, ftp_vals[4] + '/elaborati/' + filename)
                    # ----- Write historic change
                    self.pool.get('einvoice.history').create(
                        cr, uid, vals, context)
                continue
            invoice_number = filename.split('.')[0][13:].replace('_', '/')
            # ----- Search the invoice
            invoice_ids = self.search(
                cr, uid, [('number', '=', invoice_number)])
            if not invoice_ids:
                _logger.info('No invoice found for number %s' % (
                    invoice_number))
                continue
            # ----- Extract datas from XML file
            local_filename = os.path.join(r"/tmp/", filename)
            lf = open(local_filename, "wb")
            ftp.retrbinary("RETR " + filename, lf.write, 8*1024)
            lf.close()
            vals = self.read_xml_file(
                cr, uid, local_filename, invoice_ids[0], context)
            # ----- Move file in backup folder
            ftp.rename(
                filename, ftp_vals[4] + '/elaborati/' + filename)
            # ----- Write historic change
            self.pool.get('einvoice.history').create(cr, uid, vals, context)
        return True

    def force_check_einvoice_status(self, cr, uid, ids, context=None):
        return self.check_einvoice_status(cr, uid, context)

    def check_einvoice_status(self, cr, uid, ids, context=None):
        company_obj = self.pool.get('res.company')
        company_vat = company_obj.get_vat(cr, uid, False, context)
        ftp_vals = company_obj.get_ftp_vals(cr, uid, False, context)
        #try:
        ftp = FTP()
        ftp.connect(ftp_vals[0], int(ftp_vals[1]))
        ftp.login(ftp_vals[2], ftp_vals[3])
        # ----- Loop all the folders on ftp server and check files
        self.check_output_xml_pa(cr, uid, ftp, ftp_vals, company_vat,
                                 context)
        self.check_edi_state_file(cr, uid, ftp, ftp_vals, company_vat,
                                  context)
        self.check_xml_state_file(cr, uid, ftp, ftp_vals, company_vat,
                                  context)
        _logger.info('Close FTP Connection')
        ftp.quit()
        #except:
        #    raise osv.except_osv('Error', 'Error to FTP')


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


class einvoice_history(osv.osv):

    _name = "einvoice.history"

    _columns = {
        'name': fields.many2one(
            'account.invoice', 'Invoice', required=True, ondelete='cascade'),
        'date': fields.datetime('Date Action', required=True),
        'note': fields.text('Note'),
        'status_code': fields.char('Status Code', size=25),
        'status_desc': fields.text('Status Desc'),
        'xml_content': fields.text('XML File Content'),
    }

    _order = 'date'
