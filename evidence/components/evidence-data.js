// Keep exports independent of formatting: null is not zero, years/codes stay typed.
export function selectRows(rows, columns) {
  if (!Array.isArray(columns) || !columns.length || new Set(columns).size !== columns.length) {
    throw new Error('Invalid evidence columns');
  }
  return Array.from(rows, (row) => Object.fromEntries(columns.map((key) => {
    if (!Object.prototype.hasOwnProperty.call(row, key)) throw new Error(`Missing evidence column: ${key}`);
    const value = row[key];
    if (value !== null && !['string', 'number', 'boolean'].includes(typeof value)) {
      throw new Error(`Unsupported evidence value: ${key}`);
    }
    if (typeof value === 'number' && !Number.isFinite(value)) throw new Error(`Non-finite evidence value: ${key}`);
    return [key, value];
  })));
}

export function asCsv(rows, columns) {
  const cell = (value) => {
    if (value === null) return '';
    // Quoting alone does not stop spreadsheet formula execution. JSON remains
    // the unmodified, lossless alternative for these unusual text values.
    let text = String(value);
    if (typeof value === 'string' && /^[\s]*[=+\-@]/u.test(text)) text = "'" + text;
    return '"' + text.replaceAll('"', '""') + '"';
  };
  return '\uFEFF' + [columns.map(cell).join(','), ...rows.map(row => columns.map(k => cell(row[k])).join(','))].join('\r\n') + '\r\n';
}

export function saveFile(filename, content, type) {
  const url = URL.createObjectURL(new Blob([content], {type}));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
