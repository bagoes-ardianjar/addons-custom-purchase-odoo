import json
import requests
from odoo.tests import Form
import werkzeug.wrappers

from odoo import api, models, fields
from odoo import http, _, exceptions
from odoo.http import content_disposition, request
import io
import xlsxwriter

class ReportExcelAutodidakPembelianController(http.Controller):
    @http.route(['/autodidak_pembelian/autodidak_pembelian_report_excel/<model("autodidak.pembelian"):data>',], type='http', auth='user', csrs=False)
    def get_autodidak_pembelian_excel_report(self, data=None, **args):
        response = request.make_response(
            None,
            headers=[
                ('Content-Type', 'application/vnd.ms-excel'),
                ('Content-Disposition', content_disposition('Autodidak Pembelian Report' + '.xlsx'))
            ]
        )

        #membuat object workbook dari library xlsxwriter
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory' : True})

        #membuat style untuk mengatur jenis font, ukuran font, dan alignment
        atas_style = workbook.add_format({'font_name': 'Times', 'bold': True, 'align': 'left'})
        atas_isi_style = workbook.add_format({'font_name': 'Times', 'bold': False, 'align': 'left'})
        header_style = workbook.add_format({'font_name': 'Times', 'bold': True, 'left' : 1, 'right':1,'top' : 1, 'align': 'center'})
        text_style = workbook.add_format({'font_name': 'Times', 'bold': False, 'left': 1, 'right': 1, 'top': 1, 'bottom':1, 'align': 'left'})

        #looping autodidak pembelian yang dipilih oleh user
        for atas in data :
            # buat worksheet / tab per user
            sheet = workbook.add_worksheet(atas.name)

            # set orientation jadi landscape
            sheet.set_landscape()

            # set ukuran kertas dengan angka 9 yg artinya ukuran A4
            sheet.set_paper(9)

            # set margin kertas dalam satuan inchi
            sheet.set_margins(0.5, 0.5, 0.5, 0.5)

            # set lebar kolom
            sheet.set_column('A:A', 5)
            sheet.set_column('B:B', 55)
            sheet.set_column('C:C', 40)
            sheet.set_column('D:D', 15)
            sheet.set_column('E:E', 15)
            sheet.set_column('F:F', 25)
            sheet.set_column('G:G', 25)

            # set judul atas
            sheet.merge_range('A1:B1','Name', atas_style)
            sheet.merge_range('A2:B2', 'Tanggal', atas_style)

            # set isi atas
            print("aaa", atas.tanggal)
            sheet.write(0, 2, atas.name, atas_isi_style)
            sheet.write(1, 2, str(atas.tanggal), atas_isi_style)

            # set judul tabel
            sheet.write(3, 0, 'No', header_style)
            sheet.write(3, 1, 'Product', header_style)
            sheet.write(3, 2, 'Description', header_style)
            sheet.write(3, 3, 'Quantity', header_style)
            sheet.write(3, 4, 'Uom', header_style)
            sheet.write(3, 5, 'Price', header_style)
            sheet.write(3, 6, 'Sub Total', header_style)

            row = 4
            number = 1

            # cari record data autodidak pembelian yg dipilih user
            record_line = request.env['autodidak.pembelian.line'].search([('autodidak_pembelian_id', '=',atas.id)])
            for line in record_line:
                #     isi tabel
                sheet.write(row, 0, number, text_style)
                sheet.write(row, 1, line.product_id.display_name, text_style)
                sheet.write(row, 2, line.description, text_style)
                sheet.write(row, 3, line.quantity, text_style)
                sheet.write(row, 4, line.uom_id.name, text_style)
                sheet.write(row, 5, line.price, text_style)
                sheet.write(row, 6, line.sub_total, text_style)

                row += 1
                number += 1

        # memasukkan file excel yang sudah di generate ke response dan return
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
        return response

    class AutodidakPembelianRestApi(http.Controller):
        @http.route(['/api/autodidak_pembelian_get/'], type='http', auth='public', methods=['GET'], csrf=False)
        def autodidak_pembelian_resapi_get(self, **params):
            # kalau mau bikin res API per ID
            # get _id = params.get("id")
            # autodidak_pembelian = request.env['autodidak.pembelian'].sudo().search([('id', '=', get_id)])
            autodidak_pembelian = request.env['autodidak.pembelian'].sudo().search([])
            dict_autodidak_pembelian = {}
            data_autodidak_pembelian = []
            for h in autodidak_pembelian:
                dict_brand= {}
                detail_brand= []
                dict_detail_product = {}
                detail_product = []
                for b in h.brand_ids:
                    dict_brand = {'id': b.id, 'name': b.name}
                    detail_brand.append(dict_brand)
                for p in h.autodidak_pembelian_ids:
                    dict_detail_product = {'product_id': p.product_id.display_name, 'description': p.description, 'quantity': p.quantity,
                                           'uom_id': p.uom_id.name, 'price': p.price, 'sub_total': p.sub_total}
                    detail_product.append(dict_detail_product)
                    dict_autodidak_pembelian = {'id': h.id, 'name': h.name, 'brand_ids': detail_brand, 'autodidak_pembelian_ids': detail_product}
                    data_autodidak_pembelian.append(dict_autodidak_pembelian)
                data = {
                    'status': 200,
                    'message': 'success',
                    'response': data_autodidak_pembelian
                }
                try:
                    return werkzeug.wrappers.Response(
                        status=200,
                        content_type='application/json; charset=utf-8',
                        response=json.dumps(data)
                    )
                except:
                    return werkzeug.wrappers.Response(
                        status=400,
                        content_type='application/json; charset=utf-8',
                        headers=[('Access-Control-Allow-Origin', '*')],
                        response=json.dumps({
                            'error': 'Error',
                            'error_descrip': 'Error Description',
                        })
                    )

        @http.route(['/api/autodidak_pembelian_post/'], type='json', auth='public', methods=['POST'], csrf=False)
        def autodidak_pembelian_resapi_post(self, **params):
            print("abc")
            order = params.get("order")

            tanggal = order[0]['tanggal']
            brand_ids = order[0]['brands_ids']
            name_brand = []
            for a in brand_ids:
                name_brand.append(a['name'])
            brands_obj = request.env['autodidak.brand'].sudo().search([('name', 'in', name_brand)])
            autodidak_pembelian_ids = order[0]['autodidak_pembelian_ids']
            vals_line = []
            for i in autodidak_pembelian_ids:
                product_obj = request.env['product.product'].sudo().search([('default_code', '=', i['product'])])
                uom_obj = request.env['uom.uom'].sudo().search([('name', '=', i['uom'])])
                vals_line.append((0,0,{
                    'product_id' : product_obj.id,
                    'description': product_obj.name,
                    'quantity': i['quantity'],
                    'uom_id': uom_obj.id,
                    'price': i['price']
                }))
            vals_header = {
                'tanggal' : tanggal, 'brand_ids': [(6,0, brands_obj.ids)], 'autodidak_pembelian_ids': vals_line
            }
            new_autodidak_pembelian = request.env['autodidak.pembelian'].sudo().create(vals_header)
            data = {
                'status':  200,
                'message': 'success',
                'tanggal': tanggal,
                'brands': brand_ids,
                'autodidak_pembelian_ids': autodidak_pembelian_ids
            }
            return data
