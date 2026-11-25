export type InvoiceStatus = "draft" | "posted" | "partially_paid" | "paid" | "cancelled";
export type PaymentMethod = "cash" | "bank" | "mfs" | "cheque";

export interface CustomerItem {
  id: string;
  code: string;
  name: string;
  phone: string;
  email: string;
  address: string;
  bin_no: string;
  tin_no: string;
  is_active: boolean;
  created_at: string;
}

export interface InvoiceLineItem {
  id: string;
  line_no: number;
  description: string;
  quantity: string;
  unit_price: string;
  vat_rate_percent: string;
  line_subtotal: string;
  line_vat: string;
  line_total: string;
}

export interface SalesInvoiceItem {
  id: string;
  invoice_no: string;
  customer_id: string;
  invoice_date: string;
  due_date: string;
  status: InvoiceStatus;
  subtotal: string;
  vat_total: string;
  grand_total: string;
  paid_amount: string;
  notes: string;
  journal_entry_id: string | null;
  lines: InvoiceLineItem[];
  created_at: string;
}

export interface CustomerPaymentItem {
  id: string;
  payment_no: string;
  invoice_id: string;
  customer_id: string;
  payment_date: string;
  amount: string;
  payment_method: PaymentMethod;
  deposit_account_id: string;
  reference: string;
  journal_entry_id: string | null;
  created_at: string;
}
