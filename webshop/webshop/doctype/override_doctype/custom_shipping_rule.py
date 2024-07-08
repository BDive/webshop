#BDivecha
import frappe
from frappe import _, msgprint
from frappe.utils import flt, fmt_money
from erpnext.accounts.doctype.shipping_rule.shipping_rule import (
    ShippingRule
)

class CustomShippingRule(ShippingRule):
	def apply(self, doc):
		shipping_amount = 0.0
		by_value = False
		
		from_address = None
		to_address = None

		if self.custom_location_based:
			if not self.custom_capacity or float(self.custom_capacity) <=0:
				frappe.throw("Capacity not defined for shipping")
				return
			
			self.custom_capacity = float(self.custom_capacity)
			if len(doc.get('items')) > 0:
				first_item = doc.get('items')[0].item_code
			else:
				first_item = 'None-None'

			from_address = first_item.split('-')[1]
			to_address = doc.get_shipping_address().city

		
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
			shipping_amount = self.shipping_amount

		# shipping amount by value, apply conditions
		if by_value:
			shipping_amount = self.get_shipping_amount_from_rules(value, from_address, to_address)

		# convert to order currency
		if doc.currency != doc.company_currency:
			shipping_amount = flt(shipping_amount / doc.conversion_rate, 2)

		self.add_shipping_rule_to_tax_table(doc, shipping_amount)

	def get_shipping_amount_from_rules(self, value, from_address=None, to_address=None):
		if from_address and to_address:
			for condition in self.get("conditions"):
				if condition.custom_from_region.lower() == from_address.lower() and condition.custom_to_region.lower() == to_address.lower():
					return condition.shipping_amount * ((value//self.custom_capacity) + ((value % self.custom_capacity) != 0))
		else:
			for condition in self.get("conditions"):
				if not condition.to_value or (flt(condition.from_value) <= flt(value) <= flt(condition.to_value)):
					return condition.shipping_amount

		return 0.0
	
	def validate_overlapping_shipping_rule_conditions(self):
		def overlap_exists_between(num_range1, num_range2):
			"""
			num_range1 and num_range2 are two ranges
			ranges are represented as a tuple e.g. range 100 to 300 is represented as (100, 300)
			if condition num_range1 = 100 to 300
			then condition num_range2 can only be like 50 to 99 or 301 to 400
			hence, non-overlapping condition = (x1 <= x2 < y1 <= y2) or (y1 <= y2 < x1 <= x2)
			"""
			(x1, x2), (y1, y2) = num_range1, num_range2
			separate = (x1 <= x2 <= y1 <= y2) or (y1 <= y2 <= x1 <= x2)
			return not separate

		overlaps = []
		for i in range(0, len(self.conditions)):
			for j in range(i + 1, len(self.conditions)):
				d1, d2 = self.conditions[i], self.conditions[j]
				if d1.as_dict() != d2.as_dict():
					# in our case, to_value can be zero, hence pass the from_value if so
					if self.custom_location_based:
						if (d1.custom_from_region == d2.custom_from_region ) and (d1.custom_to_region == d2.custom_to_region):
							overlaps.append([d1, d2])
					else:
						range_a = (d1.from_value, d1.to_value or d1.from_value)
						range_b = (d2.from_value, d2.to_value or d2.from_value)
						if overlap_exists_between(range_a, range_b):
							overlaps.append([d1, d2])

		if overlaps:
			company_currency = frappe.get_value('Company', self.company, 'default_currency')
			msgprint(_("Overlapping conditions found between:"))
			messages = []
			for d1, d2 in overlaps:
				if self.custom_location_based:
					messages.append(
						f"Row #{d1.idx}:{d1.custom_from_region}-{d1.custom_to_region} = {fmt_money(d1.shipping_amount, currency=company_currency)} "
						+ _("and")
						+ f" Row #{d2.idx}:{d2.custom_from_region}-{d2.custom_to_region} = {fmt_money(d2.shipping_amount, currency=company_currency)}"
					)
				else:
					messages.append(
						f"Row #{d1.idx}:{d1.from_value}-{d1.to_value} = {fmt_money(d1.shipping_amount, currency=company_currency)} "
						+ _("and")
						+ f" Row #{d2.idx}:{d2.from_value}-{d2.to_value} = {fmt_money(d2.shipping_amount, currency=company_currency)}"
					)

			msgprint("\n".join(messages), raise_exception=frappe.ValidationError)