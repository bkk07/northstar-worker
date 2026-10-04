/** Format integer paise as Indian Rupees (mirrors common.money.format_inr). */
export function formatINR(paise: number): string {
  const sign = paise < 0 ? "-" : "";
  const magnitude = Math.abs(paise);
  const rupees = Math.floor(magnitude / 100);
  const remainder = magnitude % 100;
  return `${sign}₹${groupIndian(rupees.toString())}.${remainder.toString().padStart(2, "0")}`;
}

function groupIndian(digits: string): string {
  if (digits.length <= 3) return digits;
  const tail = digits.slice(-3);
  let head = digits.slice(0, -3);
  const parts: string[] = [];
  while (head.length > 2) {
    parts.unshift(head.slice(-2));
    head = head.slice(0, -2);
  }
  parts.unshift(head);
  return `${parts.join(",")},${tail}`;
}
