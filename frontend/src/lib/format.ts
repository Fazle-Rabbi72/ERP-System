/**
 * Bangladesh-specific currency and digit formatters.
 *
 * Amounts from the backend arrive as exact NUMERIC(18,2) strings so we format
 * them purely with string manipulation — never converting large amounts to
 * IEEE-754 floats where precision could be lost.
 */

const BANGLA_DIGITS: Readonly<Record<string, string>> = {
  "0": "০",
  "1": "১",
  "2": "২",
  "3": "৩",
  "4": "৪",
  "5": "৫",
  "6": "৬",
  "7": "৭",
  "8": "৮",
  "9": "৯",
};

export function toBanglaDigits(input: string): string {
  return input.replace(/[0-9]/g, (digit) => BANGLA_DIGITS[digit] ?? digit);
}

function groupLakhCrore(integerPart: string): string {
  if (integerPart.length <= 3) {
    return integerPart;
  }
  const lastThree = integerPart.slice(-3);
  const rest = integerPart.slice(0, -3);
  const groupedRest = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ",");
  return `${groupedRest},${lastThree}`;
}

export interface FormatBDTOptions {
  banglaDigits?: boolean;
  showSymbol?: boolean;
}

export function formatBDT(amount: string | number, options: FormatBDTOptions = {}): string {
  const { banglaDigits = false, showSymbol = true } = options;
  const raw = typeof amount === "number" ? amount.toFixed(2) : amount.trim();
  const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(raw);
  if (!match) {
    return showSymbol ? `৳${raw}` : raw;
  }

  const sign = match[1] ?? "";
  const intDigits = (match[2] ?? "0").replace(/^0+(?=\d)/, "");
  const fracRaw = match[3] ?? "";
  const fracDigits = fracRaw.padEnd(2, "0").slice(0, 2);

  const formatted = `${sign}${showSymbol ? "৳" : ""}${groupLakhCrore(intDigits)}.${fracDigits}`;
  return banglaDigits ? toBanglaDigits(formatted) : formatted;
}
