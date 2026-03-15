export async function api(method, url, body) {
  const options = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== undefined) {
    options.body = JSON.stringify(body);
  }
  const response = await fetch(url, options);
  if (response.status === 204) {
    return null;
  }
  const json = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(json.detail || `Error ${response.status}`);
  }
  return json;
}
