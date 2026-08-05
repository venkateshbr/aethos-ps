import { collectCompleteSseLines, toolStatusText } from './copilot.component';

describe('collectCompleteSseLines', () => {
  const wire = [
    'data: {"tool_start":"log_time_entry"}',
    '',
    'data: {"tool_result":"log_time_entry"}',
    '',
    'data: {"delta":"Prepared"}',
    '',
  ].join('\n');

  it('preserves every SSE frame across arbitrary chunk boundaries', () => {
    const expected = [
      'data: {"tool_start":"log_time_entry"}',
      'data: {"tool_result":"log_time_entry"}',
      'data: {"delta":"Prepared"}',
    ];

    for (let splitAt = 0; splitAt <= wire.length; splitAt += 1) {
      const first = collectCompleteSseLines('', wire.slice(0, splitAt));
      const second = collectCompleteSseLines(first.remainder, wire.slice(splitAt), true);
      const dataLines = [...first.lines, ...second.lines].filter(line => line.startsWith('data: '));
      expect(dataLines).withContext(`split at ${splitAt}`).toEqual(expected);
    }
  });

  it('normalises CRLF and flushes a final unterminated data line', () => {
    const batch = collectCompleteSseLines('', 'data: {"done":true}\r\n\r\ndata: final', true);
    expect(batch.lines).toEqual(['data: {"done":true}', '', 'data: final']);
    expect(batch.remainder).toBe('');
  });
});

describe('toolStatusText', () => {
  it('uses user-safe status text without exposing an internal tool name', () => {
    const internalName = 'log_time_entry';

    expect(toolStatusText(false)).toBe('Preparing secure action');
    expect(toolStatusText(true)).toBe('Secure action prepared');
    expect(toolStatusText(false)).not.toContain(internalName);
    expect(toolStatusText(true)).not.toContain(internalName);
  });
});
