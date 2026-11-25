export interface EmployeeItem {
  id: string;
  employee_code: string;
  full_name: string;
  designation: string;
  department: string;
  email: string;
  phone: string;
  nid_no: string;
  tin_no: string;
  join_date: string;
  basic_salary: string;
  house_rent_allowance: string;
  medical_allowance: string;
  conveyance_allowance: string;
  other_allowance: string;
  pf_deduction_percent: string;
  tax_deduction_amount: string;
  is_active: boolean;
  created_at: string;
}

export interface PaginatedEmployees {
  items: EmployeeItem[];
  meta: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}

export interface PayrollLineItem {
  id: string;
  employee_id: string;
  employee_code: string;
  employee_name: string;
  designation: string;
  basic_salary: string;
  allowances_total: string;
  gross_salary: string;
  pf_deduction: string;
  tax_deduction: string;
  other_deduction: string;
  total_deductions: string;
  net_salary: string;
}

export interface PayrollRunItem {
  id: string;
  run_no: string;
  pay_year: number;
  pay_month: number;
  status: string;
  total_gross: string;
  total_deductions: string;
  total_net_pay: string;
  journal_entry_id: string | null;
  notes: string;
  posted_at: string | null;
  created_at: string;
}

export interface PayrollRunDetail extends PayrollRunItem {
  lines: PayrollLineItem[];
  advisory_note: string;
}

export interface PaginatedPayrollRuns {
  items: PayrollRunItem[];
  meta: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}
