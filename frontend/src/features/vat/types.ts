export interface VatRateItem {
  id: string;
  code: string;
  name: string;
  rate_percent: string;
  is_vds_applicable: boolean;
  statutory_note: string;
  is_active: boolean;
  created_at: string;
}

export interface PaginatedVatRates {
  items: VatRateItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface Mushak61Item {
  bill_id: string;
  bill_no: string;
  bill_date: string;
  supplier_bill_ref: string;
  supplier_name: string;
  supplier_bin: string;
  taxable_value: string;
  input_vat: string;
  vds_amount: string;
  tds_amount: string;
  gross_total: string;
}

export interface Mushak61Report {
  date_from: string | null;
  date_to: string | null;
  items: Mushak61Item[];
  total_taxable_value: string;
  total_input_vat: string;
  total_vds: string;
  total_tds: string;
}

export interface Mushak62Item {
  invoice_id: string;
  invoice_no: string;
  invoice_date: string;
  customer_name: string;
  customer_bin: string;
  taxable_value: string;
  output_vat: string;
  grand_total: string;
}

export interface Mushak62Report {
  date_from: string | null;
  date_to: string | null;
  items: Mushak62Item[];
  total_taxable_value: string;
  total_output_vat: string;
  total_grand_total: string;
}

export interface Mushak63Line {
  line_no: number;
  description: string;
  quantity: string;
  unit_price: string;
  vat_rate_percent: string;
  line_subtotal: string;
  line_vat: string;
  line_total: string;
}

export interface Mushak63Challan {
  invoice_id: string;
  invoice_no: string;
  invoice_date: string;
  seller_name: string;
  customer_name: string;
  customer_bin: string;
  customer_address: string;
  lines: Mushak63Line[];
  subtotal: string;
  vat_total: string;
  grand_total: string;
}

export interface Mushak91Summary {
  date_from: string | null;
  date_to: string | null;
  total_sales_taxable: string;
  total_output_vat: string;
  total_purchase_taxable: string;
  total_input_vat: string;
  net_vat_payable: string;
  carry_forward_credit: string;
  total_vds_payable: string;
  total_tds_payable: string;
  advisory_note: string;
}
