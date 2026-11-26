let activityEpoch=0, activityRequest=0, beforeNotification=null, nextNotification=null, highestNotification=0;
function resetActivity() {
  ++activityEpoch; ++activityRequest;
  beforeNotification=null; nextNotification=null; highestNotification=0;
  document.querySelector('#activity-panel').hidden=!account;
  document.querySelector('#notification-list').replaceChildren();
  document.querySelector('#match-list').replaceChildren();
  document.querySelector('#activity-status').textContent='';
  document.querySelector('#notification-count').textContent='0 unread';
}
async function refreshActivity() {
  if(!account) return;
  const epoch=activityEpoch, sequence=++activityRequest;
  try {
    const [feed,matches]=await Promise.all([
      request('/notifications'+(beforeNotification ? '?before_id='+beforeNotification : '')), request('/matches')]);
    if(!account || epoch!==activityEpoch || sequence!==activityRequest) return;
    document.querySelector('#notification-count').textContent=feed.unread_count+' unread';
    document.querySelector('#activity-status').textContent=feed.notifications.length ? '' : 'No notifications yet.';
    nextNotification=feed.next_before_id;
    highestNotification=feed.notifications[0]?.id || 0;
    document.querySelector('#older-notifications').hidden=!nextNotification;
    document.querySelector('#latest-notifications').hidden=!beforeNotification;
    document.querySelector('#read-notifications').disabled=!highestNotification;
    const list=document.querySelector('#notification-list'); list.replaceChildren();
    feed.notifications.forEach(n=>{
      const row=element('article','','notification-row'+(n.read_at ? '' : ' unread'));
      row.append(element('p',n.text),element('small',new Date(n.created_at).toLocaleString()));
      const buttons=element('div','','claim-actions');
      const open=element('button',n.kind==='message'?'Open conversation':n.kind==='claim'?'View claim':'View possible match','secondary');
      open.type='button';
      open.addEventListener('click',async()=>{
        open.disabled=true;
        try {
          if(n.kind==='message') {
            const history=await request(`/conversations/${n.resource_id}/messages`);
            if(epoch!==activityEpoch) return;
            await openChat(history.conversation);
          } else if(n.kind==='claim') {
            await refreshClaims();
            if(epoch!==activityEpoch) return;
            const card=[...document.querySelectorAll('#claims-list article')].find(c=>c.dataset.claimId===n.resource_id);
            (card || document.querySelector('#claims-panel')).scrollIntoView({block:'center'});
          } else await showDetails(n.report_id);
          if(epoch!==activityEpoch) return;
          await request(`/notifications/${n.id}/read`,{method:'POST',body:'{}'});
          await refreshActivity();
        } catch(error) { if(epoch===activityEpoch) document.querySelector('#activity-status').textContent=error.message; }
        finally {open.disabled=false;}
      });
      buttons.append(open);
      if(!n.read_at) {
        const read=element('button','Mark read','secondary'); read.type='button';
        read.addEventListener('click',async()=>{
          read.disabled=true;
          try {await request(`/notifications/${n.id}/read`,{method:'POST',body:'{}'}); if(epoch===activityEpoch) await refreshActivity();}
          catch(error){if(epoch===activityEpoch) document.querySelector('#activity-status').textContent=error.message; read.disabled=false;}
        });
        buttons.append(read);
      }
      row.append(buttons); list.append(row);
    });
    const suggestions=document.querySelector('#match-list'); suggestions.replaceChildren();
    if(!matches.length) suggestions.append(element('p','No close matches yet. Suggestions will appear when another report has similar details.'));
    matches.forEach(match=>{
      const card=element('article','','match-card');
      card.append(element('h3',match.title),element('p','Possible match for your report: '+match.own_title),
        element('p',`${match.report_type === 'found' ? 'Found' : 'Lost'} at ${match.location} · ${match.date}`),
        element('p',match.reasons.join(' · ')));
      const view=element('button','Compare reports','secondary'); view.type='button';
      view.addEventListener('click',()=>showDetails(match.report_id));
      const own=element('button','View your report','secondary'); own.type='button';
      own.addEventListener('click',()=>showDetails(match.own_report_id));
      const actions=element('div','','claim-actions'); actions.append(view,own); card.append(actions); suggestions.append(card);
    });
  } catch(error) {
    if(epoch===activityEpoch) document.querySelector('#activity-status').textContent=error.message;
  }
}
document.querySelector('#refresh-activity').addEventListener('click',refreshActivity);
document.querySelector('#older-notifications').addEventListener('click',()=>{beforeNotification=nextNotification;refreshActivity();});
document.querySelector('#latest-notifications').addEventListener('click',()=>{beforeNotification=null;refreshActivity();});
document.querySelector('#read-notifications').addEventListener('click',async()=>{
  const epoch=activityEpoch;
  try {await request('/notifications/read-all',{method:'POST',body:JSON.stringify({through_id:highestNotification})}); if(epoch===activityEpoch) await refreshActivity();}
  catch(error){if(epoch===activityEpoch) document.querySelector('#activity-status').textContent=error.message;}
});
setInterval(()=>{if(account && !document.hidden) refreshActivity();},10000);
document.addEventListener('visibilitychange',()=>{if(account && !document.hidden) refreshActivity();});
