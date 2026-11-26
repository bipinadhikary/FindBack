const form = document.querySelector('#report-form');
const filters = document.querySelector('#filters');
const message = document.querySelector('#form-message');
const listMessage = document.querySelector('#list-message');
const dialog = document.querySelector('#details');
let csrfToken = '';
let account = null;
let registering = false;
let selectedPhotos = [];
let previewUrls = [];
const photoInput = document.querySelector('#photo-input');
function renderPhotoPreviews() {
  previewUrls.forEach(url => URL.revokeObjectURL(url));
  previewUrls = [];
  const container = document.querySelector('#photo-previews');
  container.replaceChildren();
  selectedPhotos.forEach((file, index) => {
    const figure = document.createElement('figure');
    const img = document.createElement('img');
    img.src = URL.createObjectURL(file);
    previewUrls.push(img.src);
    img.alt = `Selected photo ${index + 1}`;
    const remove = element('button', 'Remove', 'secondary');
    remove.type = 'button';
    remove.setAttribute('aria-label', `Remove photo ${index + 1}`);
    remove.addEventListener('click', () => {
      selectedPhotos.splice(index, 1);
      photoInput.value = '';
      renderPhotoPreviews();
    });
    figure.append(img, element('figcaption', file.name), remove);
    container.append(figure);
  });
}
function resetPhotos() {
  selectedPhotos = [];
  photoInput.value = '';
  photoInput.setCustomValidity('');
  document.querySelector('#photo-message').textContent = '';
  renderPhotoPreviews();
}
photoInput.addEventListener('change', () => {
  const files = [...photoInput.files];
  const error = files.length > 3 ? 'Choose up to 3 photos.' :
    files.some(file => file.size > 5 * 1024 * 1024) ? 'Each photo must be 5 MB or smaller.' :
    files.some(file => !['image/jpeg','image/png','image/webp'].includes(file.type)) ? 'Use JPEG, PNG or WebP photos.' : '';
  selectedPhotos = error ? [] : files;
  photoInput.setCustomValidity(error);
  document.querySelector('#photo-message').textContent = error;
  renderPhotoPreviews();
});
function encodePhoto(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve({data: reader.result.split(',')[1]});
    reader.onerror = () => reject(new Error('Could not read the selected photo'));
    reader.readAsDataURL(file);
  });
}
function syncPickup() {
  const found = form.elements.report_type.value === 'found';
  const staff = ['reception','admin'].includes(account?.role);
  const fields = document.querySelector('#pickup-fields');
  fields.hidden = !found;
  fields.disabled = !found;
  document.querySelector('#location-label').textContent = found ? 'Where was it found?' : 'Where was it lost?';
  document.querySelector('#reception-custody').disabled = !staff;
  document.querySelector('#reception-note').hidden = staff;
  if (!staff && form.elements.custody.value === 'reception') form.elements.custody.value = 'finder';
  const reception = found && form.elements.custody.value === 'reception';
  form.elements.collection_location.required = reception;
  document.querySelector('#collection-label').textContent = reception ? 'Collection location' : 'Suggested meeting location (optional)';
}
form.elements.report_type.addEventListener('change', syncPickup);
form.elements.custody.addEventListener('change', syncPickup);
function photoElement(photo, title, className = '') {
  const img = document.createElement('img');
  img.src = photo.url;
  img.alt = `Photo of ${title}`;
  img.loading = 'lazy';
  img.className = className;
  return img;
}
const categoryLabels = new Map();
function categoryLabel(report) {
  return report.category === 'other' ? `Other · ${report.custom_category}` : (categoryLabels.get(report.category) || report.category);
}
function syncCustomCategory() {
  const other = form.elements.category.value === 'other';
  document.querySelector('#custom-category-label').hidden = !other;
  form.elements.custom_category.disabled = !other;
  form.elements.custom_category.required = other;
  if (!other) form.elements.custom_category.value = '';
}
form.elements.category.addEventListener('change', syncCustomCategory);
async function loadCategories() {
  const groups = await request('/static/categories.json');
  form.elements.category.replaceChildren(new Option('Choose a category', ''));
  filters.elements.category.replaceChildren(new Option('All categories', ''));
  for (const group of groups) {
    for (const select of [form.elements.category, filters.elements.category]) {
      const options = document.createElement('optgroup');
      options.label = group.group;
      for (const item of group.items) {
        categoryLabels.set(item.value, item.label);
        options.append(new Option(item.label, item.value));
      }
      select.append(options);
    }
  }
  form.elements.category.disabled = false;
  syncCustomCategory();
}
const now = new Date();
const today = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
form.elements.date.max = today;
form.elements.date.value = today;
async function request(url, options) {
  const headers = {...(options?.headers || {})};
  if (options?.method && options.method !== 'GET') {
    headers['Content-Type'] = 'application/json';
    if (csrfToken) headers['X-CSRF-Token'] = csrfToken;
  }
  const response = await fetch(url, {...options, headers, credentials: 'same-origin'});
  if (response.status === 204) return null;
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401 && account) setAccount(null);
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
  const viewer = account?.id;
  const content = document.querySelector('#detail-content');
  content.textContent = 'Loading report…';
  dialog.showModal();
  try {
    const r = await request(`/reports/${encodeURIComponent(id)}`);
    if (!account || account.id !== viewer) return;
    content.replaceChildren(element('h2', r.title));
    for (const [label, value] of [['Type',r.report_type],['Category',categoryLabel(r)],['Description',r.description],[r.report_type === 'found' ? 'Found at' : 'Lost at',r.location],['Date',r.date],['Status',r.status],['Report ID',r.id]]) content.append(element('p',`${label}: ${value}`));
    if (r.report_type === 'found') {
      content.append(element('p', `Held by: ${r.custody === 'reception' ? 'Reception' : r.custody === 'finder' ? 'Finder' : 'Not recorded'}`));
      if (r.collection_location) content.append(element('p', `${r.custody === 'reception' ? 'Collect from' : 'Suggested meeting location'}: ${r.collection_location}`));
      if (r.pickup_instructions) content.append(element('p', `Pickup instructions: ${r.pickup_instructions}`));
    }
    if (r.photos?.length) {
      const gallery = element('div', '', 'photo-grid detail-photos');
      r.photos.forEach(photo => gallery.append(photoElement(photo, r.title)));
      content.append(gallery);
    }
    if (r.report_type === 'found' && r.owner_id && r.owner_id !== account.id) {
      const chatButton = element('button', r.custody === 'reception' ? 'Message reception' : 'Message finder');
      chatButton.type = 'button';
      chatButton.addEventListener('click', async () => {
        chatButton.disabled = true;
        try {
          const conversation = await request(`/reports/${encodeURIComponent(r.id)}/conversations`, {method:'POST', body:'{}'});
          if (!account || account.id !== viewer) return;
          dialog.close();
          await openChat(conversation);
        } catch (error) { content.append(element('p', error.message, 'error')); }
        finally { chatButton.disabled = false; }
      });
      content.append(chatButton);
    } else if (r.report_type === 'found' && !r.owner_id) {
      content.append(element('p', 'Messaging is unavailable because this older report has no assigned owner.'));
    } else if (r.owner_id === account.id) {
      content.append(element('p', 'Check your inbox for conversations about this item.'));
    }
    if (typeof addClaimForm === 'function') addClaimForm(r, content);
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
      card.append(element('span',`${r.report_type.toUpperCase()} · ${categoryLabel(r)} · ${r.status === 'resolved' ? 'Returned' : 'Open'}`,'badge'),element('h3',r.title),element('p',`${r.location} · ${r.date}`),button);
      if (r.photos?.length) card.insertBefore(photoElement(r.photos[0], r.title, 'report-photo'), button);
      if (r.report_type === 'found' && r.collection_location) card.insertBefore(element('p', `${r.custody === 'reception' ? 'Collect from' : 'Meeting location'}: ${r.collection_location}`), button);
      container.append(card);
    }
  } catch (error) { if (sequence === listRequest) listMessage.textContent = `Could not load reports: ${error.message}`; }
}
form.addEventListener('submit', async event => {
  event.preventDefault();
  const button = form.querySelector('button[type="submit"]');
  button.disabled = true;
  message.className = '';
  message.textContent = 'Saving…';
  try {
    const payload = Object.fromEntries(new FormData(form));
    for (const field of ['collection_location', 'pickup_instructions']) if (!payload[field]) delete payload[field];
    payload.photos = await Promise.all(selectedPhotos.map(encodePhoto));
    await request('/reports',{method:'POST',body:JSON.stringify(payload)});
    form.reset(); form.elements.date.value = today; syncCustomCategory(); syncPickup(); resetPhotos();
    filters.reset();
    message.textContent = 'Report saved. It will remain after a server restart.';
    if (typeof refreshActivity === 'function') refreshActivity();
    await loadReports();
  } catch (error) { message.className = 'error'; message.textContent = error.message; }
  finally { button.disabled = false; }
});
filters.addEventListener('submit', event => {event.preventDefault(); loadReports();});
document.querySelector('#close-details').addEventListener('click',() => dialog.close());

function setAccount(session) {
  account = session?.user || null;
  csrfToken = session?.csrf_token || '';
  if (typeof resetChat === 'function') resetChat();
  if (typeof resetClaims === 'function') resetClaims();
  if (typeof resetActivity === 'function') resetActivity();
  ++listRequest;
  document.querySelector('#account-panel').hidden = !!account;
  document.querySelector('#app-panel').hidden = !account;
  document.querySelector('#logout').hidden = !account;
  document.querySelector('#admin-panel').hidden = account?.role !== 'admin';
  document.querySelector('#account-label').textContent = account ? `${account.display_name} · ${account.role}` : 'Campus community';
  document.querySelector('#reports').replaceChildren();
  document.querySelector('#admin-users').replaceChildren();
  document.querySelector('#detail-content').replaceChildren();
  dialog.close();
  form.reset();
  syncCustomCategory();
  syncPickup();
  resetPhotos();
  form.elements.date.value = today;
  if (account) {
    loadReports();
    if (typeof refreshInbox === 'function') refreshInbox();
    if (typeof refreshClaims === 'function') refreshClaims();
    if (typeof refreshActivity === 'function') refreshActivity();
    if (account.role === 'admin') loadUsers();
  }
}

document.querySelector('#account-toggle').addEventListener('click', () => {
  registering = !registering;
  document.querySelector('#account-heading').textContent = registering ? 'Create your account' : 'Sign in to FindBack';
  document.querySelector('#name-label').hidden = !registering;
  document.querySelector('#account-form').elements.display_name.required = registering;
  document.querySelector('#account-form').elements.password.autocomplete = registering ? 'new-password' : 'current-password';
  document.querySelector('#account-submit').textContent = registering ? 'Create account' : 'Sign in';
  document.querySelector('#account-toggle').textContent = registering ? 'I already have an account' : 'Create an account';
  document.querySelector('#account-message').textContent = '';
});

document.querySelector('#account-form').addEventListener('submit', async event => {
  event.preventDefault();
  const authForm = event.currentTarget;
  const button = document.querySelector('#account-submit');
  const status = document.querySelector('#account-message');
  const data = Object.fromEntries(new FormData(authForm));
  if (!registering) delete data.display_name;
  button.disabled = true;
  status.textContent = 'Please wait…';
  try {
    const session = await request(registering ? '/auth/register' : '/auth/login', {method: 'POST', body: JSON.stringify(data)});
    authForm.reset();
    status.textContent = '';
    setAccount(session);
  } catch (error) { status.textContent = error.message; }
  finally { button.disabled = false; }
});

document.querySelector('#logout').addEventListener('click', async () => {
  try {
    await request('/auth/logout', {method: 'POST', body: '{}'});
    setAccount(null);
  } catch (error) { listMessage.textContent = error.message; }
});

async function loadUsers() {
  const status = document.querySelector('#admin-message');
  status.textContent = 'Loading accounts…';
  try {
    const users = await request('/admin/users');
    if (account?.role !== 'admin') return;
    const container = document.querySelector('#admin-users');
    container.replaceChildren();
    for (const user of users) {
      const row = element('div', '', 'staff-row');
      row.append(element('span', `${user.display_name} (${user.email}) · ${user.role}`));
      if (user.role !== 'admin') {
        const button = element('button', user.role === 'reception' ? 'Remove reception access' : 'Assign reception access', 'secondary');
        button.addEventListener('click', async () => {
          button.disabled = true;
          try {
            await request(`/admin/users/${encodeURIComponent(user.id)}/role`, {method: 'PATCH', body: JSON.stringify({role: user.role === 'reception' ? 'user' : 'reception'})});
            await loadUsers();
          } catch (error) { status.textContent = error.message; button.disabled = false; }
        });
        row.append(button);
      }
      container.append(row);
    }
    status.textContent = '';
  } catch (error) { status.textContent = error.message; }
}
document.querySelector('#refresh-users').addEventListener('click', loadUsers);
loadCategories().then(() => request('/auth/me').then(setAccount).catch(() => setAccount(null))).catch(() => {
  document.querySelector('#account-submit').disabled = true;
  document.querySelector('#account-message').textContent = 'Could not load categories. Refresh to try again.';
});
