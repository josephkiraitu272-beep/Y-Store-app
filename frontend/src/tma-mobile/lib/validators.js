/**
 * Validators for Checkout
 * Блокуємо "4 цифри незрозумілі", емодзі, символи — лише літери, дефіси, апостроф і пробіл.
 */

// Буквы UA/RU/EN + " ' - space
const NAME_RE = /^[А-ЯЁІЇЄҐа-яёіїєґA-Za-z\s'\u2019-]+$/;
const CITY_RE = /^[А-ЯЁІЇЄҐа-яёіїєґA-Za-z\s'\u2019.\-()]+$/;

export function validateName(value, { minLen = 2, field = "Поле" } = {}) {
  const v = (value || '').trim();
  if (!v) return `${field} обов'язкове`;
  if (v.length < minLen) return `${field}: мінімум ${minLen} символи`;
  if (v.length > 40) return `${field} занадто довге`;
  if (/\d/.test(v)) return `${field} не повинно містити цифр`;
  if (!NAME_RE.test(v)) return `${field}: дозволені лише літери, дефіс та апостроф`;
  return null;
}

export function validateCity(value) {
  const v = (value || '').trim();
  if (!v) return "Оберіть місто зі списку";
  if (v.length < 2) return "Вкажіть принаймні 2 літери";
  if (!CITY_RE.test(v)) return "Місто має містити тільки літери";
  return null;
}

export function validatePhoneUA(value) {
  const digits = (value || '').replace(/\D/g, '');
  if (!digits) return "Вкажіть номер телефону";
  if (!digits.startsWith('380')) return "Номер має починатись з +380";
  if (digits.length !== 12) return "Невірна довжина номера (+380 XX XXX XX XX)";
  // Перевіримо що другий блок (оператор) 2 цифри — Ukrainian mobile operators range
  const op = digits.slice(3, 5);
  const validOperators = ['39', '50', '63', '66', '67', '68', '73', '91', '92', '93', '94', '95', '96', '97', '98', '99'];
  if (!validOperators.includes(op)) return "Невідомий оператор (коди: 50, 63, 66, 67, 68, 73, 93, 95, 96, 97, 98, 99)";
  return null;
}

export function validateBranch(value, { cityRef } = {}) {
  const v = (value || '').trim();
  if (!v) return "Оберіть відділення зі списку";
  if (!cityRef) return "Спочатку оберіть місто";
  return null;
}

/** Capitalize first letter of each word — для красивого вводу ПІБ */
export function capitalizeName(value) {
  return (value || '')
    .replace(/[^А-ЯЁІЇЄҐа-яёіїєґA-Za-z\s'\u2019-]/g, '') // strip digits/symbols inline
    .split(' ')
    .map(w => (w ? w[0].toUpperCase() + w.slice(1) : ''))
    .join(' ');
}
