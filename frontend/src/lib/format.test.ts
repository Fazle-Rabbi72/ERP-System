import { describe, expect, it } from "vitest";

import { formatBDT, toBanglaDigits } from "@/lib/format";

describe("BDT lakh/crore formatter & Bangla digits", () => {
  it("formats thousands, lakhs, and crores accurately without float loss", () => {
    expect(formatBDT("500")).toBe("৳500.00");
    expect(formatBDT("1234567.89")).toBe("৳12,34,567.89");
    expect(formatBDT("10000000.00")).toBe("৳1,00,00,000.00");
    // 18-digit NUMERIC(18,2) string beyond JS Number.MAX_SAFE_INTEGER
    expect(formatBDT("1234567890123456.78")).toBe("৳1,23,45,67,89,01,23,456.78");
  });

  it("handles negative numbers and optional symbol", () => {
    expect(formatBDT("-250000.5")).toBe("-৳2,50,000.50");
    expect(formatBDT("150000", { showSymbol: false })).toBe("1,50,000.00");
  });

  it("converts to Bangla digits when requested", () => {
    expect(formatBDT("1234567.89", { banglaDigits: true })).toBe("৳১২,৩৪,৫৬৭.৮৯");
    expect(toBanglaDigits("2026-11-25")).toBe("২০২৬-১১-২৫");
  });
});
