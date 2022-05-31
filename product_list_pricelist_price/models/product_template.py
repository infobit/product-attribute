# Copyright 2021 ForgeFlow, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from lxml import etree

from odoo import api, fields, models
from odoo.exceptions import UserError,Warning

from odoo.addons.base.models.ir_ui_view import (
    transfer_modifiers_to_node,
    transfer_node_to_modifiers,
)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _compute_product_template_pricelist_price(self):
        pricelists = self.env["product.pricelist"].search(
            [("display_pricelist_price", "=", True)]
        )
        result = pricelists.price_rule_get_multi(
            [(product, 1.0, False) for product in self]
        )
        #product_list={}
        for product in self:
            for pricelist in pricelists:
                field_name = "product_tmpl_price_pricelist_%s" % (pricelist.id)
                product[field_name] = (
                    pricelist.currency_id.round(result[product.id][pricelist.id][0])
                    if result[product.id][pricelist.id] and result[product.id][pricelist.id][0]
                    else 0.0
                )

    def _compute_product_template_pricelist_margin(self):
        pricelists = self.env["product.pricelist"].search(
            [("display_pricelist_price", "=", True)]
        )
        result = pricelists.price_rule_get_multi(
            [(product, 1.0, False) for product in self]
        )
        for product in self:
            for pricelist in pricelists:
                field_name = "product_tmpl_margin_pricelist_%s" % (pricelist.id)
                product[field_name] = (
                    ( 
                        ( pricelist.currency_id.round( result[product.id][pricelist.id][0] ) - product.standard_price )
                        / pricelist.currency_id.round( result[product.id][pricelist.id][0] )
                        )
                    if result[product.id][pricelist.id] and result[product.id][pricelist.id][0]
                    else 0.0
                )


    def _set_product_template_pricelist_price(self):
        pricelists = self.env["product.pricelist"].search(
            [("display_pricelist_price", "=", True)]
        )
        # TODO: comprobar tipo de linea y modificar si es de producto 
        # o crear una nueva linea para el producto en cuestion
        result = pricelists.price_rule_get_multi(
            [(product, 1.0, False) for product in self]
        )
        for product in self:
            for pricelist in pricelists:
                field_name = "product_tmpl_price_pricelist_%s" % (pricelist.id)
                if product[field_name] != 0.0: # check value:
                    rule_id = result[product.id][pricelist.id][1]
                    rule = self.env["product.pricelist.item"].browse([rule_id])
                    if rule.applied_on in ['3_global','2_product_category'] or not rule:
                        values = {
                            'compute_price':'fixed',
                            'applied_on':'1_product',
                            'product_tmpl_id':product.id,
                            'fixed_price':product[field_name],
                            'pricelist_id':pricelist.id
                        } 
                        self.env["product.pricelist.item"].create(values)
                    else:
                        rule.fixed_price = product[field_name]

    def _set_product_template_pricelist_margin(self):
        pricelists = self.env["product.pricelist"].search(
            [("display_pricelist_price", "=", True)]
        )
        # TODO: comprobar tipo de linea y modificar si es de producto 
        # o crear una nueva linea para el producto en cuestion
        # P=C/(1-(MB/100) )
        result = pricelists.price_rule_get_multi(
            [(product, 1.0, False) for product in self]
        )
        for product in self:
            for pricelist in pricelists:
                field_name = "product_tmpl_margin_pricelist_%s" % (pricelist.id)
                if product[field_name] != 0.0: # check value:
                    rule_id = result[product.id][pricelist.id][1]
                    rule = self.env["product.pricelist.item"].browse([rule_id])
                    #raise Warning(product[field_name])
                    if rule.applied_on in ['3_global','2_product_category'] or not rule:
                        values = {
                            'compute_price':'fixed',
                            'applied_on':'1_product',
                            'product_tmpl_id':product.id,
                            'fixed_price': product.standard_price / (1-product[field_name]),
                            'pricelist_id':pricelist.id
                        } 
                        self.env["product.pricelist.item"].create(values)
                    else:
                        rule.fixed_price = product.standard_price / ( (1 - product[field_name]) )

    @api.model
    def fields_view_get(
        self, view_id=None, view_type="form", toolbar=False, submenu=False
    ):
        result = super(ProductTemplate, self).fields_view_get(
            view_id, view_type, toolbar=toolbar, submenu=submenu,
        )
        doc = etree.XML(result["arch"])
        name = result.get("name", False)

        if name == "product.template.pricelist.price":
            for placeholder in doc.xpath("//field[@name='type']"):
                for pricelist in self.env["product.pricelist"].search(
                    [("display_pricelist_price", "=", True)]
                ):

                    field_name = "product_tmpl_price_pricelist_%s" % (pricelist.id)
                    tag_name = "Sales Price (%s)" % (pricelist.name)
                    elem = etree.Element(
                        "field",
                        {"name": field_name, 
                        "widget":"monetary"
                        #"readonly": "True", 
                        #"optional": "hide"
                        },
                    )
                    modifiers = {}
                    transfer_node_to_modifiers(elem, modifiers)
                    transfer_modifiers_to_node(elem, modifiers)
                    placeholder.addnext(elem)
                    result["fields"].update(
                        {
                            field_name: {
                                "domain": [],
                                "context": {},
                                "string": tag_name,
                                "type": "float",
                            }
                        }
                    )

                    field_name = "product_tmpl_margin_pricelist_%s" % (pricelist.id)
                    tag_name = "Margin Price (%s)" % (pricelist.name)
                    elem = etree.Element(
                        "field",
                        {"name": field_name, 
                        "widget":"percentage"
                        #"readonly": "True", 
                        #"optional": "hide"
                        },
                    )
                    modifiers = {}
                    transfer_node_to_modifiers(elem, modifiers)
                    transfer_modifiers_to_node(elem, modifiers)
                    placeholder.addnext(elem)
                    result["fields"].update(
                        {
                            field_name: {
                                "domain": [],
                                "context": {},
                                "string": tag_name,
                                "type": "float",
                            }
                        }
                    )

                result["arch"] = etree.tostring(doc)
        return result

    @api.model
    def _add_pricelist_price(self, field_name, tag_name):
        self._add_field(
            field_name,
            fields.Float(
                string=tag_name, 
                compute="_compute_product_template_pricelist_price",
                inverse="_set_product_template_pricelist_price"
            ),
        )
        return True

    @api.model
    def _add_pricelist_margin(self, field_name, tag_name):
        self._add_field(
            field_name,
            fields.Float(
                string=tag_name, 
                compute="_compute_product_template_pricelist_margin",                
                inverse="_set_product_template_pricelist_margin"
            ),
        )
        return True

    def _register_hook(self):
        pricelists = self.env["product.pricelist"].search(
            [("display_pricelist_price", "=", True)]
        )
        for pricelist in pricelists:
            field_name = "product_tmpl_price_pricelist_%s" % (pricelist.id)
            tag_name = "Sales Price (%s)" % (pricelist.name)
            if field_name in self._fields:
                continue
            self._add_pricelist_price(field_name, tag_name)

            field_margin_name = "product_tmpl_margin_pricelist_%s" % (pricelist.id)
            tag_margin_name = "Margin Price (%s)" % (pricelist.name)
            if field_margin_name in self._fields:
                continue
            self._add_pricelist_margin(field_margin_name, tag_margin_name)

        self._setup_fields()
        self._setup_complete()
        return super(ProductTemplate, self)._register_hook()
