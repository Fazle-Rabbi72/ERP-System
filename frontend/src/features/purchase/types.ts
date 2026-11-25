export type BillStatus = "draft" | "posted" | "partially_paid" | "paid" | "cancelled";
export type PaymentMethod = "cash" | "bank" | "mfs" | "cheque";

export interface SupplierItem {
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

export interface PurchaseBillItem {
  id: string;
  bill_no: string;
  supplier_bill_ref: string;
  supplier_id: string;
  expense_account_id: string;
  bill_date: string;
  due_date: string;
  status: BillStatus;
  subtotal: string;
  vat_total: string;
  gross_total: string;
  tds_rate_percent: string;
  tds_amount: string;
  vds_rate_percent: string;
  vds_amount: string;
  net_payable: string;
  paid_amount: string;
  notes: string;
  journal_entry_id: string | null;
  created_at: string;
}

export interface SupplierPaymentItem {
  id: string;
  payment_no: string;
  bill_id: string;
  supplier_id: string;
  payment_date: string;
  amount: string;
  payment_method: PaymentMethod;
  payment_account_id: string;
  reference: string;
  journal_entry_id: string | null;
  created_at: string;
}
