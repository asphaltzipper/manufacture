# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.addons import decimal_precision as dp


class MrpBomComponentFindWizard(models.TransientModel):
    _name = 'mrp.bom.component.find.wizard'

    product_id = fields.Many2one('product.product', 'Component', required=True)

    @api.multi
    def mrp_bom_component_find(self, wizard_id, component_id, level):

        cr = self._cr
        cr.execute("""
            select comp_id, product_qty, product_tmpl_id, mb_id, parent_id from (
            with recursive clean_bom (parent_prod_id, comp_prod_id, product_tmpl_id, mb_id,
            product_qty) as (
            select
                b.product_id as parent_prod_id,
                l.product_id as comp_prod_id,
                b.product_tmpl_id as product_tmpl_id,
                b.id as mb_id,
                l.product_qty
            from mrp_bom_line as l
            inner join mrp_bom as b on b.id=l.bom_id
            ),
            bom_struct(comp_id, parent_id,  product_tmpl_id, mb_id, product_qty) as (
            select
                b.comp_prod_id,
                b.parent_prod_id,
                b.product_tmpl_id,
                b.mb_id, 
                b.product_qty
            from clean_bom as b
            where b.comp_prod_id=%s
            union
                select
                    b.comp_prod_id,
                    b.parent_prod_id,
                    b.product_tmpl_id,
                    b.mb_id,
                    b.product_qty
             from clean_bom as b
             inner join bom_struct as c on c.parent_id=b.comp_prod_id
            )
            select
                p.comp_id,
                p.parent_id,
                b.product_qty,
                b.mb_id,
                b.product_tmpl_id
            from bom_struct as p
            left join clean_bom as b on b.parent_prod_id=p.parent_id and 
            b.comp_prod_id=p.comp_id
            order by p.comp_id, p.parent_id
            ) as t """, (str(component_id),))

        result = cr.fetchall()
        for row in result:
            compose_id = row[4]
            vals = {
                    'wizard_id': wizard_id,
                    'component_id': row[0],
                    'parent_id': compose_id,
                    'quantity': row[1],
                    'mrp_bom_id': row[3],
            }
            self.env['mrp.bom.component.find.line'].create(vals)

    @api.multi
    def do_search_component(self):
        for obj in self:
            if obj.product_id:
                # pdb.set_trace()
                self.mrp_bom_component_find(obj.id, obj.product_id.id, 1)
        return {
            'name': "Component find %s " % obj.product_id.name,
            'view_mode': 'tree,form',
            'view_type': 'tree',
            'res_model': 'mrp.bom.component.find.line',
            'type': 'ir.actions.act_window',
            'domain': [('wizard_id', '=', obj.id),
                       ('component_id', '=', obj.product_id.id)],
        }


class MrpBomComponentFindLine(models.TransientModel):
    _name = 'mrp.bom.component.find.line'

    wizard_id = fields.Many2one('mrp.bom.component.find.wizard', 'Wizard')
    level = fields.Char('Level')
    component_id = fields.Many2one('product.product', 'Component')
    parent_id = fields.Many2one('product.product', 'Component')
    line = fields.Integer('Line')
    quantity = fields.Float(
        'Quantity', digits=dp.get_precision('Product Unit of Measure'))
    mrp_bom_id = fields.Many2one('mrp.bom', 'Product')
    parent_ids = fields.One2many(
        comodel_name='mrp.bom.component.find.line',
        compute='_compute_parent_ids')

    def _compute_parent_ids(self):
        for obj in self:
            domain = [
                ('wizard_id', '=', obj.wizard_id.id),
                ('component_id', '=', obj.parent_id.id),
            ]
            obj.parent_ids = obj.search(domain)
