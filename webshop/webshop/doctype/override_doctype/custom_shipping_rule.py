#BDivecha
import frappe
from frappe.utils import flt
from erpnext.accounts.doctype.shipping_rule.shipping_rule import (
    ShippingRule
)


class CustomShippingRule(ShippingRule):
	def apply(self, doc):
		shipping_amount = 0.0
		by_value = False
		
        #BDivecha
		add_shipping_amount = 0.0
		if "pick" not in self.label.lower() and self.custom_location_based:
			if not doc.custom_distance:
				frappe.throw("Distance required on address")
			else:
				add_shipping_amount = self.get_shipping_amount_from_location(doc.custom_distance)

		if doc.get_shipping_address():
			# validate country only if there is address
			self.validate_countries(doc)

		if self.calculate_based_on == "Net Total":
			value = doc.base_net_total
			by_value = True

		elif self.calculate_based_on == "Net Weight":
			value = doc.total_net_weight
			by_value = True

		elif self.calculate_based_on == "Fixed":
			shipping_amount = add_shipping_amount + self.shipping_amount

		# shipping amount by value, apply conditions
		if by_value:
			shipping_amount = add_shipping_amount + self.get_shipping_amount_from_rules(value)

		# convert to order currency
		if doc.currency != doc.company_currency:
			shipping_amount = flt(shipping_amount / doc.conversion_rate, 2)

		self.add_shipping_rule_to_tax_table(doc, shipping_amount)
		
	def get_shipping_amount_from_location(self, value):
		for condition in self.get("custom_location_conditions"):
			if not condition.to_value or (flt(condition.from_value) <= flt(value) <= flt(condition.to_value)):
				return condition.shipping_amount
			else:
				frappe.throw(f"Distance: {value}km. Shipping is currently not available for your location")

		return 0.0