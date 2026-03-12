export async function fetchYard() {
  const res = await fetch(`/yard?_t=${Date.now()}`);
  if (!res.ok) throw new Error('API error');
  return res.json();
}

export async function initYard(config) {
  const res = await fetch('/yard/init', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error('Init error');
  return res.json();
}
