let activeConversation = null;
let chatEpoch = 0;
let chatCursor = 0;
let loadingChat = false;
let inboxVersion = 0;
const chatDrafts = new Map();
const chatBody = document.querySelector('#chat-body');
const chatStatus = document.querySelector('#chat-status');

function resetChat() {
  ++chatEpoch;
  ++inboxVersion;
  activeConversation = null;
  chatCursor = 0;
  loadingChat = false;
  chatDrafts.clear();
  document.querySelector('#inbox-panel').hidden = !account;
  document.querySelector('#chat-panel').hidden = true;
  document.querySelector('#conversation-list').replaceChildren();
  document.querySelector('#chat-messages').replaceChildren();
  document.querySelector('#inbox-status').textContent = '';
  document.querySelector('#unread-count').textContent = '0 unread';
  chatStatus.textContent = '';
  chatBody.value = '';
}

async function refreshInbox() {
  if (!account) return;
  const epoch = chatEpoch;
  const version = ++inboxVersion;
  try {
    const inbox = await request('/conversations');
    if (!account || epoch !== chatEpoch || version !== inboxVersion) return;
    document.querySelector('#unread-count').textContent = `${inbox.unread_count} unread`;
    document.querySelector('#inbox-status').textContent = inbox.conversations.length ? '' : 'No conversations yet. Open a found item to message its finder or reception.';
    const list = document.querySelector('#conversation-list');
    list.replaceChildren();
    inbox.conversations.forEach(conversation => {
      const text = `${conversation.title}\n${conversation.other_name}${conversation.unread_count ? ' · ' + conversation.unread_count + ' unread' : ''}\n${conversation.last_message.slice(0, 100) || 'Start the conversation'}`;
      const button = element('button', text, 'conversation secondary');
      button.type = 'button';
      button.setAttribute('aria-pressed', String(activeConversation?.id === conversation.id));
      button.addEventListener('click', () => openChat(conversation));
      list.append(button);
    });
  } catch (error) {
    if (epoch === chatEpoch) document.querySelector('#inbox-status').textContent = error.message;
  }
}

async function openChat(conversation) {
  if (!account) return;
  if (activeConversation) {
    const previous = chatDrafts.get(activeConversation.id);
    chatDrafts.set(activeConversation.id, {body:chatBody.value,
      client_id: previous?.body === chatBody.value.trim() ? previous.client_id : undefined});
  }
  ++chatEpoch;
  activeConversation = conversation;
  chatCursor = 0;
  loadingChat = false;
  document.querySelector('#chat-panel').hidden = false;
  document.querySelector('#chat-heading').textContent = conversation.title;
  document.querySelector('#chat-person').textContent = `Chat with ${conversation.other_name}`;
  document.querySelector('#chat-messages').replaceChildren();
  chatBody.value = chatDrafts.get(conversation.id)?.body || '';
  chatStatus.textContent = '';
  document.querySelector('#send-message').disabled = false;
  document.querySelector('#chat-panel').scrollIntoView({block:'nearest'});
  await fetchMessages();
  await refreshInbox();
}

async function fetchMessages() {
  if (!account || !activeConversation || loadingChat) return;
  loadingChat = true;
  const epoch = chatEpoch;
  const conversationId = activeConversation.id;
  const log = document.querySelector('#chat-messages');
  const stickToBottom = chatCursor === 0 || log.scrollHeight - log.scrollTop - log.clientHeight < 80;
  try {
    let more = true;
    while (more) {
      const result = await request(`/conversations/${conversationId}/messages?after_id=${chatCursor}`);
      if (!account || epoch !== chatEpoch) return;
      result.messages.forEach(message => {
        const mine = message.sender_id === account.id;
        const bubble = element('div', '', 'chat-message' + (mine ? ' mine' : ''));
        bubble.append(element('strong', mine ? 'You' : result.conversation.other_name),
                      element('p', message.body), element('small', new Date(message.created_at).toLocaleString()));
        log.append(bubble);
        chatCursor = message.id;
      });
      more = result.has_more;
    }
    if (stickToBottom) log.scrollTop = log.scrollHeight;
    if (!document.hidden && chatCursor) {
      await request(`/conversations/${conversationId}/read`, {method:'POST', body:JSON.stringify({last_message_id:chatCursor})});
    }
  } catch (error) {
    if (epoch === chatEpoch) chatStatus.textContent = error.message;
  } finally {
    if (epoch === chatEpoch) loadingChat = false;
  }
}

document.querySelector('#chat-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (!account || !activeConversation) return;
  const body = chatBody.value.trim();
  if (!body) { chatStatus.textContent = 'Enter a message.'; return; }
  const conversationId = activeConversation.id;
  const epoch = chatEpoch;
  const previous = chatDrafts.get(conversationId);
  const draft = previous?.body === body && previous.client_id ? previous : {body, client_id:crypto.randomUUID()};
  chatDrafts.set(conversationId, draft);
  const button = document.querySelector('#send-message');
  button.disabled = true;
  chatStatus.textContent = 'Sending…';
  try {
    await request(`/conversations/${conversationId}/messages`, {method:'POST', body:JSON.stringify(draft)});
    chatDrafts.delete(conversationId);
    if (epoch !== chatEpoch || !account) return;
    if (chatBody.value.trim() === body) chatBody.value = '';
    chatStatus.textContent = '';
    await fetchMessages();
    await refreshInbox();
  } catch (error) {
    if (epoch === chatEpoch) chatStatus.textContent = error.message;
  } finally {
    if (epoch === chatEpoch) button.disabled = false;
  }
});
document.querySelector('#refresh-inbox').addEventListener('click', async () => { await fetchMessages(); await refreshInbox(); });
document.querySelector('#chat-item').addEventListener('click', () => {
  if (activeConversation) showDetails(activeConversation.report_id);
});
setInterval(async () => {
  if (document.hidden || !account) return;
  await fetchMessages();
  await refreshInbox();
}, 5000);
document.addEventListener('visibilitychange', async () => {
  if (!document.hidden && account) { await fetchMessages(); await refreshInbox(); }
});
