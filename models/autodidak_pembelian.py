from odoo import models, fields, api, _
from datetime import date, datetime
from odoo.exceptions import ValidationError

import xlrd
import base64
import os

def load_data(sheet):
    data = []
    offset = 0
    for row in range(sheet.nrows):
        if row-offset == 0:
            col_codes = []
            for col in range(sheet.ncols):
                value = sheet.cell(row, col).value
                if type(value) == str:
                    value = value.strip()
                col_codes.append(value)
        elif row-offset > 0:
            new_line = {}
            for col in range(sheet.ncols):
                new_line[col_codes[col]] = sheet.cell(row, col).value
            data.append(new_line)
    return data

class autodidak_pembelian(models.Model):
    _name = 'autodidak.pembelian'

    def get_excel_report(self):
        #     redirect ke controller /autodidak_pembelian/autodidak_pembelian_report_excel/
        return {
            'type': 'ir.actions.act_url',
            'url': '/autodidak_pembelian/autodidak_pembelian_report_excel/%s' % (self.id),
            'terget': 'new'
        }
    def func_delete_status_draft(self):
        autodidak_pembelian_obj = self.env['autodidak.pembelian'].search([('status', '=', 'draft')])
        for line in autodidak_pembelian_obj:
            line.unlink()
        return True

    def show_tree_view(self):
        tree_view_id = self.env['ir.model.data'].xmlid_to_res_id('autodidak_pembelian.autodidak_pembelian_tree_view_id')
        form_view_id = self.env['ir.model.data'].xmlid_to_res_id('autodidak_pembelian.autodidak_pembelian_form_view_id')
        domain = [('status', '=', 'draft')]
        result = {
            'name' : 'Pembelian B',
            'type' : 'ir.actions.act_window',
            'views' : [[tree_view_id, 'tree'],[form_view_id, 'form']],
            'target' : 'current',
            'res_model' : 'autodidak.pembelian',
            'domain' : domain,
            'limit' : 40
        }
        return result

    @api.model
    def create(self, values):
        res = super(autodidak_pembelian, self).create(values)
        for rec in res:
            tanggal_pembelian = rec.tanggal
            tanggal_sekarang = date.today()
            if tanggal_pembelian < tanggal_sekarang:
                raise ValidationError(_("Tanggal yang diinput tidak boleh kurang dari tanggal sekarang"))
        return res

    def write(self, values):
        res = super(autodidak_pembelian, self).write(values)
        if 'tanggal' in values:
            tanggal_pembelian = self.tanggal
            tanggal_sekarang= date.today()
            if tanggal_pembelian < tanggal_sekarang:
                raise ValidationError(_("Tanggal yang diinput tidak boleh kurang dari tanggal saai ini"))
        return res
    def func_to_approve(self):
        for line in self:
            if line.status == 'draft':
                if line.name == 'New':
                    seq = self.env['ir.sequence'].next_by_code('autodidak.pembelian') or '/'
                    line.name = seq
                line.status = 'to_approve'

    def func_approved(self):
        if self.status == 'to_approve':
            self.status = 'approved'

    def func_done(self):
        if self.status == 'approved':
            self.status = 'done'

    name = fields.Char(string='Name', default="New")
    tanggal = fields.Date(string="Tanggal")
    status = fields.Selection([('draft','Draft'),('to_approve','To Approve'),('approved','Approved'),('done','Done')], default='draft')
    autodidak_pembelian_ids = fields.One2many('autodidak.pembelian.line',  'autodidak_pembelian_id', string="Autodidak Pembelian Ids")
    brand_ids = fields.Many2many('autodidak.brand', 'autodidak_pembelian_brand_rel', 'autodidak_pembelian_id', 'brand_id', string="Brand Ids")

class autodidak_pembelian_line(models.Model):
    _name = 'autodidak.pembelian.line'

    @api.onchange('product_id')
    def func_onchange_product_id(self):
        if not self.product_id:
            return{}
        else:
            self.description = self.product_id.name
            return {}

    def _func_amount_total(self):
        for line in self:
            line.sub_total = line.quantity * line.price

    # def _func_domain_product_id(self):
    #     product_obj = self.env['product.product'].search([('type', '=', 'product')])
    #     domain = [('id', 'in', product_obj.ids)]
    #     return domain

    name = fields.Char(string='Name')
    autodidak_pembelian_id = fields.Many2one('autodidak.pembelian', string="Autodidak Pembelian Id")
    product_id = fields.Many2one('product.product', string="Product Id")
    description = fields.Char(string="Description")
    quantity = fields.Float(string='Quantity', default=0.0)
    price = fields.Float(string="Price", default=0.0)
    sub_total = fields.Float(string="Sub Total", compute=_func_amount_total)
    uom_id = fields.Many2one('uom.uom', string="Uom Id")

class autodidak_brand(models.Model):
    _name = 'autodidak.brand'

    name = fields.Char(string='Name')

class autodidak_pembelian_report_wizard(models.TransientModel):
    _name = 'autodidak.pembelian.report.wizard'

    name = fields.Char(string="Name")
    periode_awal = fields.Date(string="Periode Awal")
    periode_akhir = fields.Date(string="Periode Akhir")

class product_template(models.Model):
    _inherit = 'product.template'

    def _get_product_qrcode(self):
        for rec in self:
            rec.product_qrcode = str(rec.id)

    def func_approve(self):
        if self.status == 'draft':
            self.status = 'approved'

    def print_qrcode(self):
        return {
            'type' : 'ir.actions.report',
            'report_name' : 'autodidak_pembelian.report_autodidak_pembelian_qrcode_id',
            'report_type' : 'qweb-pdf',
        }

    status = fields.Selection([('draft','Draft'),('to_approve','To Approve'),('approved','Approved'),('done','Done')], default='draft')
    product_qrcode = fields.Char(string="Product QR Code", compute=_get_product_qrcode)

class base_import(models.TransientModel):
    _inherit = 'base_import.import'

    file_import = fields.Binary(string="File Import")
    file_name_import = fields.Char(string="File Name Import")

    def actions_import_autodidak_pembelian(self):
        data_product = []
        dict_autodidak_pembelian = {}
        autodidak_pembelian_obj = self.env['autodidak.pembelian']
        if self.file_import:
            filename, file_extension = os.path.splitext(self.file_name_import)
            if file_extension == '.xlsx' or file_extension == '.xls':
                book = xlrd.open_workbook(file_contents=base64.decodestring(self.file_import))
                sheet = book.sheet_by_index(0)
                data = load_data(sheet)
                for row in data:
                    # Pengambilan Data Tanggal
                    check_tanggal = row['Tanggal']
                    type_check_tanggal = type(check_tanggal)
                    if type_check_tanggal == float:
                        calculation_tanggal = (check_tanggal - 25569) * 86400
                        tanggal = datetime.utcfromtimestamp(calculation_tanggal).date()
                    else:
                        tanggal = check_tanggal.strip()

                    # Pengambilan Data Brands
                    check_brands = row['Brands'].strip()
                    brands = []
                    if check_brands != '':
                        get_name_brand = []
                        split_brand = check_brands.split(',')
                        for i in split_brand:
                            get_name_brand.append(i.strip())
                            brands_obj = self.env['autodidak.brand'].search([('name', 'in',get_name_brand)])
                            brands = brands_obj.ids

                    # Pengambilan data product
                    check_product = row['Product'].strip()
                    if check_product != '':
                        split_product = str(check_product).split(' ')[0]
                        replace_product_name = (split_product.replace('[', '')).replace(']', '')
                        product_obj = self.env['product.product'].search([('default_code', '=', replace_product_name)])
                        if product_obj:
                            product = product_obj.id
                        else:
                            product = None
                    else:
                        product = None

                    # Pengambilan data description
                    description = row['Description'].strip()

                    # Pengambilan data quantity
                    check_quantity = row['Quantity']
                    if check_quantity != '':
                        quantity = float(check_quantity)
                    else:
                        quantity = 0.0

                    # Pengambilan data uom
                    check_uom = row['Uom'].strip()
                    if check_uom != '':
                        uom_obj = self.env['uom.uom'].search([('name', '=', check_uom)])
                        if uom_obj:
                            uom = uom_obj.id
                        else:
                            uom = None
                    else:
                        uom = None

                    # Pengambilan data price
                    check_price = row['Price']
                    if check_price != '':
                        price = float(check_price)
                    else:
                        price = 0.0

                    # Catatan angka
                    # 0 = create
                    # 1 = update
                    # 2 = remove
                    # 3 = cut dari beberapa object
                    # 4 = link existing record
                    # 5 = delete all
                    # 6 = replace

                    values_header = {
                        'tanggal' : tanggal,
                        'brand_ids' : [(6, 0, brands)],
                        'autodidak_pembelian_ids' : [(0, 0, {
                            'product_id' : product,
                            'description': description,
                            'quantity' : quantity,
                            'uom_id': uom,
                            'price' : price
                        })]
                    }
                    new_autodidak_pembelian_id = autodidak_pembelian_obj.create(values_header)
                tree_view_id = self.env['ir.model.data'].xmlid_to_res_id('autodidak_pembelian.autodidak_pembelian_tree_view_id')
                form_view_id = self.env['ir.model.data'].xmlid_to_res_id('autodidak_pembelian.autodidak_pembelian_form_view_id')
                return {
                    'name' : 'Autodidak Pembelian',
                    'view_type' : 'form',
                    'view_mode' : 'tree,form',
                    'type' : 'ir.actions.act_window',
                    'res_model': 'autodidak.pembelian',
                    'views': [[tree_view_id, 'tree'],[form_view_id, 'form']]
                }