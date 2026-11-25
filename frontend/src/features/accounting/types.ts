export type AccountType = "asset" | "liability" | "equity" | "revenue" | "expense";
export type NormalBalance = "debit" | "credit";
export type JournalStatus = "draft" | "posted" | "reversed";

export interface AccountItem {
  id: string;
  code: string;
  name: string;
  account_type: AccountType;
  normal_balance: NormalBalance;
  parent_id: string | null;
  is_group: boolean;
  is_active: boolean;
  description: string;
  created_at: string;
}

export interface JournalLineItem {
  id: string;
  account_id: string;
  line_no: number;
  description: string;
  debit: string;
  credit: string;
}

export interface JournalEntryItem {
  id: string;
  voucher_no: string;
  entry_date: string;
  reference: string;
  narration: string;
  status: JournalStatus;
  posted_at: string | null;
  posted_by: string | null;
  reversed_entry_id: string | null;
  lines: JournalLineItem[];
  created_at: string;
}

export interface TrialBalanceLine {
  account_id: string;
  code: string;
  name: string;
  account_type: AccountType;
  normal_balance: NormalBalance;
  total_debit: string;
  total_credit: string;
  net_debit: string;
  net_credit: string;
}

export interface TrialBalanceResponse {
  as_of_date: string | null;
  rows: TrialBalanceLine[];
  grand_total_debit: string;
  grand_total_credit: string;
  is_balanced: boolean;
}
