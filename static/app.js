const form = document.querySelector('#report-form');
const filters = document.querySelector('#filters');
const message = document.querySelector('#form-message');
const listMessage = document.querySelector('#list-message');
const dialog = document.querySelector('#details');
const now = new Date();
const today = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
form.elements.date.max = today;
form.elements.date.value = today;
async function request(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    const detail = Array.isArray(data.detail) ? data.detail.map(e => `${e.loc.slice(1).join('.')}: ${e.msg}`).join('; ') : data.detail;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return data;
}
function element(tag, text, className) {
  const node = document.createElement(tag);
  node.textContent = text;
  if (className) node.className = className;
  return node;
}
async function showDetails(id) {
  const content = document.querySelector('#detail-content');
  content.textContent = 'Loading report…';
  dialog.showModal();
  try {
    const r = await request(`/reports/${encodeURIComponent(id)}`);
    content.replaceChildren(element('h2', r.title));
    for (const [label, value] of [['Type',r.report_type],['Category',r.category],['Description',r.description],['Location',r.location],['Date',r.date],['Status',r.status],['Report ID',r.id]]) content.append(element('p',`${label}: ${value}`));
  } catch (error) { content.textContent = error.message; }
}
let listRequest = 0;
async function loadReports() {
  const sequence = ++listRequest;
  listMessage.textContent = 'Loading reports…';
  try {
    const params = new URLSearchParams();
    for (const [key,value] of new FormData(filters)) if (value.trim()) params.set(key,value.trim());
    const reports = await request(`/reports?${params}`);
    if (sequence !== listRequest) return;
    const container = document.querySelector('#reports');
    container.replaceChildren();
    listMessage.textContent = reports.length ? `${reports.length} report(s)` : 'No reports match. Create a report or change your filters.';
    for (const r of reports) {
      const card = element('article','','card');
      const button = element('button','View details','secondary');
      button.addEventListener('click',() => showDetails(r.id));
      card.append(element('span',`${r.report_type.toUpperCase()} · ${r.category}`,'badge'),element('h3',r.title),element('p',`${r.location} · ${r.date}`),button);
      container.append(card);
    }
  } catch (error) { if (sequence === listRequest) listMessage.textContent = `Could not load reports: ${error.message}`; }
}
form.addEventListener('submit', async event => {
  event.preventDefault();
  const button = form.querySelector('button');
  button.disabled = true;
  message.className = '';
  message.textContent = 'Saving…';
  try {
    await request('/reports',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(new FormData(form)))});
    form.reset(); form.elements.date.value = today;
    filters.reset();
    message.textContent = 'Report saved. It will remain after a server restart.';
    await loadReports();
  } catch (error) { message.className = 'error'; message.textContent = error.message; }
  finally { button.disabled = false; }
});
filters.addEventListener('submit', event => {event.preventDefault(); loadReports();});
document.querySelector('#close-details').addEventListener('click',() => dialog.close());
loadReports();
