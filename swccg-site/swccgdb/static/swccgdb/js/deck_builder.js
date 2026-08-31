/**
 * Shared add/remove/qty/filter behavior for a deck-builder page (a searchable list of
 * available cards on the left, the deck's current contents on the right). Used by both
 * swccgdb's physical-collection deck editor and game's GameDeck editor.
 *
 * Expects, on the page:
 *   #card-count            badge showing "N/60", updated after every change
 *   #available-body        <tbody> of candidate rows, each with data-item-id, data-name
 *                           (lowercased, for search), data-type (filter/display), and
 *                           optionally data-side (filter/display) when config.hasSideFilter
 *   #deck-body              <tbody> of current deck rows (same data-item-id convention)
 *   #cardSearch, #cardType  filter inputs; #cardSide too when config.hasSideFilter
 *   .btn-add-card / .btn-remove-card / .btn-qty[data-dir]   action buttons (delegated)
 *
 * config:
 *   baseUrl        e.g. "/decks/" or "/play/decks/" (deck id + action get appended)
 *   deckId
 *   idParam         POST field name the server expects, e.g. "owned_card_id" or "card_id"
 *   hasSideFilter   whether a #cardSide filter is present
 *   emptyRowHtml    <tr> markup to show when the deck has no cards
 *   buildRow(itemId, sourceRow)  returns the HTML string for a newly-added deck row
 */
function initDeckBuilder(config) {
  const CSRF = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';

  function post(action, data) {
    return fetch(`${config.baseUrl}${config.deckId}/${action}/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams(data),
    }).then(r => r.json());
  }

  function updateCount(total) {
    const el = document.getElementById('card-count');
    el.textContent = total + '/60';
    el.className = 'badge fs-6 ' + (total >= 60 ? 'bg-success' : total >= 50 ? 'bg-warning text-dark' : 'bg-secondary');
    if (config.onCountChange) config.onCountChange(total);
  }

  function removeEmptyRow() {
    const e = document.getElementById('empty-row');
    if (e) e.remove();
  }

  function maybeAddEmptyRow() {
    if (document.querySelectorAll('#deck-body tr').length === 0) {
      document.getElementById('deck-body').innerHTML = config.emptyRowHtml;
    }
  }

  function applyFilter() {
    const name = document.getElementById('cardSearch').value.toLowerCase();
    const type = document.getElementById('cardType').value;
    const side = config.hasSideFilter ? document.getElementById('cardSide').value : null;
    document.querySelectorAll('#available-body tr[data-item-id]').forEach(row => {
      const match = row.dataset.name.includes(name)
        && (!type || row.dataset.type === type)
        && (!config.hasSideFilter || !side || row.dataset.side === side);
      row.style.display = match ? '' : 'none';
    });
  }
  document.getElementById('cardSearch').addEventListener('input', applyFilter);
  document.getElementById('cardType').addEventListener('change', applyFilter);
  if (config.hasSideFilter) {
    document.getElementById('cardSide').addEventListener('change', applyFilter);
  }

  // Once the deck has any card in it, lock the side filter to that card's side so you
  // can't even browse (let alone try to add) a card of the wrong side. Unlocks again
  // once the deck is emptied back out.
  function applySideLock() {
    if (!config.hasSideFilter) return;
    const sideSelect = document.getElementById('cardSide');
    const firstDeckRow = document.querySelector('#deck-body tr[data-item-id]');
    const lockedSide = firstDeckRow ? firstDeckRow.dataset.side : null;
    sideSelect.disabled = !!lockedSide;
    sideSelect.value = lockedSide || '';
    applyFilter();
  }
  applySideLock();

  document.getElementById('available-body').addEventListener('click', e => {
    const btn = e.target.closest('.btn-add-card');
    if (!btn || btn.disabled) return;
    const itemId = btn.dataset.itemId;
    const row = btn.closest('tr');

    post('add-card', { [config.idParam]: itemId }).then(data => {
      if (data.error) { alert(data.error); return; }
      btn.textContent = 'Added';
      btn.disabled = true;
      btn.classList.replace('btn-outline-light', 'btn-secondary');
      updateCount(data.total);
      removeEmptyRow();

      const tr = document.createElement('tr');
      tr.dataset.itemId = itemId;
      tr.dataset.type = row.dataset.type;
      if (config.hasSideFilter) {
        tr.dataset.side = row.dataset.side;
      }
      tr.innerHTML = config.buildRow(itemId, row);
      document.getElementById('deck-body').appendChild(tr);
      applySideLock();
    });
  });

  document.getElementById('deck-body').addEventListener('click', e => {
    const removeBtn = e.target.closest('.btn-remove-card');
    if (removeBtn) {
      const itemId = removeBtn.dataset.itemId;
      post('remove-card', { [config.idParam]: itemId }).then(data => {
        if (data.error) { alert(data.error); return; }
        removeBtn.closest('tr').remove();
        updateCount(data.total);
        maybeAddEmptyRow();
        applySideLock();
        const addBtn = document.querySelector(`#available-body .btn-add-card[data-item-id="${itemId}"]`);
        if (addBtn) {
          addBtn.textContent = 'Add';
          addBtn.disabled = false;
          addBtn.classList.replace('btn-secondary', 'btn-outline-light');
        }
      });
      return;
    }

    const qtyBtn = e.target.closest('.btn-qty');
    if (qtyBtn) {
      const itemId = qtyBtn.dataset.itemId;
      const tr = qtyBtn.closest('tr');
      const qtyEl = tr.querySelector('.qty-val');
      const next = parseInt(qtyEl.textContent) + parseInt(qtyBtn.dataset.dir);
      if (next < 1) return;
      post('update-card', { [config.idParam]: itemId, quantity: next }).then(data => {
        if (data.error) { alert(data.error); return; }
        qtyEl.textContent = data.quantity;
        updateCount(data.total);
      });
    }
  });
}
