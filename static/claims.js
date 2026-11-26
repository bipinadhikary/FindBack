let claimEpoch = 0;
let claimRequest = 0;
const claimLabels = {pending:'Pending review',approved:'Approved — awaiting handover',rejected:'Rejected',
  withdrawn:'Withdrawn',returned:'Returned',closed:'Closed — item returned to another claimant'};

function resetClaims() {
  ++claimEpoch;
  ++claimRequest;
  document.querySelector('#claims-panel').hidden = !account;
  document.querySelector('#claims-list').replaceChildren();
  document.querySelector('#claims-status').textContent = '';
}

async function refreshClaims() {
  if (!account) return;
  const epoch = claimEpoch, sequence = ++claimRequest;
  try {
    const claims = await request('/claims');
    if (!account || epoch !== claimEpoch || sequence !== claimRequest) return;
    const list = document.querySelector('#claims-list');
    list.replaceChildren();
    document.querySelector('#claims-status').textContent = claims.length ? '' : 'No claims yet.';
    claims.forEach(claim => {
      const card = element('article','','claim-card');
      card.dataset.claimId = claim.id;
      card.append(element('h3',claim.title),
        element('p',`${claim.is_owner ? 'Claim from ' + claim.claimant_name : 'Your claim'} · ${claimLabels[claim.status]}`));
      const proof = document.createElement('details');
      proof.append(element('summary','Private identifying details'),element('p',claim.proof));
      card.append(proof);
      if (claim.note) card.append(element('p',claim.note));
      const history = document.createElement('details');
      history.append(element('summary','Claim history'));
      claim.events.forEach(event => history.append(element('p',`${new Date(event.created_at).toLocaleString()} · ${claimLabels[event.status]}${event.note ? ' · ' + event.note : ''}`)));
      card.append(history);
      const item = element('button','View item','secondary');
      item.type = 'button';
      item.addEventListener('click',()=>showDetails(claim.report_id));
      card.append(item);
      if (['pending','approved'].includes(claim.status) && claim.report_status === 'open') {
        const status = element('p',''); status.setAttribute('role','status');
        const controls = element('div','','claim-actions');
        const noteLabel = element('label','Note (optional)');
        const note = document.createElement('textarea'); note.maxLength = 500; note.rows = 2;
        noteLabel.append(note);
        let verified = null;
        if (claim.is_owner) {
          card.append(noteLabel);
          if (claim.status === 'approved' || claim.custody === 'reception') {
            const label = element('label','','verify-return');
            verified = document.createElement('input'); verified.type = 'checkbox';
            label.append(verified,document.createTextNode('I checked ownership and handed the item to this claimant.'));
            card.append(label);
          }
        }
        const action = (name, label) => {
          const button = element('button',label,name === 'reject' || name === 'withdraw' ? 'secondary' : '');
          button.type = 'button';
          button.addEventListener('click',async()=>{
            if (name === 'confirm_return' && !verified?.checked) { status.textContent = 'Confirm the ownership check and handover first.'; return; }
            controls.querySelectorAll('button').forEach(b=>b.disabled=true);
            try {
              await request(`/claims/${claim.id}/actions`,{method:'POST',body:JSON.stringify({action:name,note:note.value,verified:!!verified?.checked})});
              if (epoch !== claimEpoch) return;
              await refreshClaims(); await loadReports();
              if (typeof refreshActivity === 'function') refreshActivity();
            } catch(error) {
              if (epoch === claimEpoch) status.textContent=error.message;
              controls.querySelectorAll('button').forEach(b=>b.disabled=false);
            }
          });
          controls.append(button);
        };
        if (!claim.is_owner) action('withdraw','Withdraw claim');
        else {
          const canManage = claim.custody !== 'reception' || ['admin','reception'].includes(account.role);
          if (canManage) {
            if (claim.custody !== 'reception' && claim.status === 'pending') action('approve','Approve claim');
            action('reject','Reject claim');
            if (verified) action('confirm_return',claim.custody === 'reception' ? 'Confirm collection' : 'Confirm handover');
          } else status.textContent = 'Reception access is required to manage this claim.';
        }
        card.append(controls,status);
      }
      list.append(card);
    });
  } catch(error) {
    if (epoch === claimEpoch) document.querySelector('#claims-status').textContent=error.message;
  }
}

function addClaimForm(report, container) {
  if (report.report_type !== 'found') return;
  const section = element('section','','claim-card');
  container.append(section);
  if (report.status === 'resolved') { section.append(element('p','This item has been returned. New claims are closed.')); return; }
  if (!report.owner_id) { section.append(element('p','Claims are unavailable until this report has an owner.')); return; }
  if (report.owner_id === account.id) { section.append(element('p','Review requests in Claims and returns.')); return; }
  const epoch = claimEpoch;
  section.append(element('h3','Claim this item'),
    element('p','Describe a distinguishing detail that proves it is yours. Only you and the report owner can see your claim.'));
  if (report.custody === 'reception') section.append(element('p','Reception will verify ownership in person before confirming collection.'));
  const claimForm = document.createElement('form');
  const label = element('label','Private identifying details');
  const proof = document.createElement('textarea');
  proof.required=true; proof.minLength=10; proof.maxLength=2000; proof.rows=3;
  label.append(proof);
  const submit = element('button','Submit claim'); submit.type='submit';
  const status=element('p',''); status.setAttribute('role','status');
  claimForm.append(label,submit,status); section.append(claimForm);
  claimForm.addEventListener('submit',async event=>{
    event.preventDefault(); submit.disabled=true;
    try {
      await request(`/reports/${report.id}/claims`,{method:'POST',body:JSON.stringify({proof:proof.value})});
      if (epoch !== claimEpoch) return;
      section.replaceChildren(element('p','Claim saved. Track it in Claims and returns.'));
      await refreshClaims();
    } catch(error) { if (epoch === claimEpoch) status.textContent=error.message; submit.disabled=false; }
  });
}
document.querySelector('#refresh-claims').addEventListener('click',refreshClaims);
