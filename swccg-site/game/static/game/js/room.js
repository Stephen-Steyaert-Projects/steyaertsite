const lobbyUrl = document.currentScript.dataset.lobbyUrl;

const roomCode = JSON.parse(document.getElementById('room-code').textContent);
const userId = JSON.parse(document.getElementById('user-id').textContent);
const lightDecks = JSON.parse(document.getElementById('light-decks').textContent);
const darkDecks = JSON.parse(document.getElementById('dark-decks').textContent);
const SIDE_LABELS = { D: 'Dark Side', L: 'Light Side' };
const SIDE_CARD_BACK_CLASS = { D: 'card-back-dark', L: 'card-back-light' };

const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const socket = new WebSocket(`${protocol}//${window.location.host}/ws/game/${roomCode}/`);

const statusEl = document.getElementById('connection-status');
const playersConnectedEl = document.getElementById('players-connected');
const waitingPanel = document.getElementById('waiting-panel');
const readyPanel = document.getElementById('ready-panel');
const readyDeckSelect = document.getElementById('ready-deck-select');
const readyBtn = document.getElementById('ready-btn');
const locationSelectRow = document.getElementById('location-select-row');
const locationSelect = document.getElementById('location-select');
const confirmLocationBtn = document.getElementById('confirm-location-btn');
const readyStatusEl = document.getElementById('ready-status');
const readyErrorEl = document.getElementById('ready-error');
const chatLog = document.getElementById('chat-log');
const closeRoomBtn = document.getElementById('close-room-btn');

// Game-table overlays
const statusOverlay = document.getElementById('status-overlay');
const opponentHandOverlay = document.getElementById('opponent-hand-overlay');
const handOverlay = document.getElementById('hand-overlay');
const forceOverlay = document.getElementById('force-overlay');
const turnControlsOverlay = document.getElementById('turn-controls-overlay');
const resultBanner = document.getElementById('game-result-banner');
const phaseErrorEl = document.getElementById('phase-error');
const passPhaseBtn = document.getElementById('pass-phase-btn');
const resignBtn = document.getElementById('resign-btn');
const rematchBtn = document.getElementById('rematch-btn');
const activateForceRow = document.getElementById('activate-force-row');
const activateForceInput = document.getElementById('activate-force-input');
const activateForceBtn = document.getElementById('activate-force-btn');
const drawCardsRow = document.getElementById('draw-cards-row');
const drawCardsInput = document.getElementById('draw-cards-input');
const drawCardsBtn = document.getElementById('draw-cards-btn');
const chatWidget = document.getElementById('chat-widget');
const chatToggleBtn = document.getElementById('chat-toggle-btn');
const chatPanelBody = document.getElementById('chat-panel-body');
const chatUnreadDot = document.getElementById('chat-unread-dot');
const myPileCluster = document.getElementById('my-pile-cluster');
const oppPileCluster = document.getElementById('opp-pile-cluster');
const myPileStacks = document.querySelectorAll('#my-pile-cluster .pile-stack:not(.pile-lost)');
const oppPileStacks = document.querySelectorAll('#opp-pile-cluster .pile-stack:not(.pile-lost)');

let currentStatus = null;
let myHand = [];
let isChatOpen = false;

socket.addEventListener('open', () => {
  statusEl.className = 'alert alert-success';
  statusEl.textContent = 'Connected';
});

let kickedMessage = null;
let navigateAfterClose = null;

socket.addEventListener('close', () => {
  if (navigateAfterClose) {
    window.location.href = navigateAfterClose;
    return;
  }
  statusEl.className = 'alert alert-danger';
  statusEl.textContent = kickedMessage || 'Disconnected';
  passPhaseBtn.disabled = true;
});

socket.addEventListener('message', (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'state') {
    renderState(data);
  } else if (data.type === 'error') {
    readyErrorEl.textContent = data.message;
    phaseErrorEl.textContent = data.message;
  } else if (data.type === 'kicked') {
    kickedMessage = data.message;
  } else if (data.type === 'location_options') {
    locationSelect.innerHTML = data.locations.map(l => `<option value="${l.id}">${l.name}</option>`).join('');
    locationSelectRow.classList.remove('d-none');
  } else if (data.type === 'your_hand') {
    myHand = data.cards;
    renderMyHand();
  } else if (data.type === 'chat') {
    const line = document.createElement('div');
    line.textContent = `${data.username}: ${data.text}`;
    chatLog.appendChild(line);
    chatLog.scrollTop = chatLog.scrollHeight;
    if (!isChatOpen) {
      chatUnreadDot.classList.remove('d-none');
    }
  }
});

// Keeps idle-turn detection ticking over even if the waiting player never sends anything.
setInterval(() => {
  if (socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'ping' }));
  }
}, 30000);

function setPileBackClass(stacks, side) {
  const backClass = SIDE_CARD_BACK_CLASS[side] || 'card-back-dark';
  stacks.forEach(el => {
    el.classList.remove('card-back-light', 'card-back-dark');
    el.classList.add(backClass);
  });
}

function renderMyHand() {
  handOverlay.innerHTML = myHand.map(card => {
    const style = card.image_url ? ` style="background-image: url('${card.image_url}')"` : '';
    return `<div class="hand-card"${style}><div class="hand-card-label">${card.name}</div></div>`;
  }).join('');
}

function renderState(data) {
  playersConnectedEl.textContent = `${data.connected_user_ids.length} / 2 players connected`;
  currentStatus = data.status;

  const isInProgress = data.status === 'in_progress';
  const isGameOver = data.status === 'game_over';
  const isTableVisible = isInProgress || isGameOver;

  const isCreator = data.creator_user_id === userId;
  closeRoomBtn.classList.toggle('d-none', !isCreator || isInProgress);
  const mySide = data.side_by_user_id[String(userId)];

  waitingPanel.classList.toggle('d-none', data.status !== 'waiting_for_player');
  readyPanel.classList.toggle('d-none', data.status !== 'awaiting_ready');

  statusOverlay.classList.toggle('d-none', !isTableVisible);
  opponentHandOverlay.classList.toggle('d-none', !isTableVisible);
  handOverlay.classList.toggle('d-none', !isTableVisible);
  forceOverlay.classList.toggle('d-none', !isTableVisible);
  turnControlsOverlay.classList.toggle('d-none', !isTableVisible);
  myPileCluster.classList.toggle('d-none', !isTableVisible);
  oppPileCluster.classList.toggle('d-none', !isTableVisible);

  if (data.status === 'awaiting_ready') {
    document.getElementById('ready-game-number').textContent = data.game_number;
    document.getElementById('my-side').textContent = SIDE_LABELS[mySide] || '—';

    const decks = mySide === 'D' ? darkDecks : lightDecks;
    readyDeckSelect.innerHTML = decks.map(d => `<option value="${d.id}">${d.name}</option>`).join('');

    const iAmReady = data.ready_user_ids.includes(userId);
    const iChoseLocation = data.location_chosen_user_ids.includes(userId);
    readyBtn.disabled = iAmReady;
    readyDeckSelect.disabled = iAmReady;

    locationSelectRow.classList.toggle('d-none', !iAmReady || iChoseLocation);
    confirmLocationBtn.disabled = iChoseLocation;
    locationSelect.disabled = iChoseLocation;

    if (!iAmReady) {
      readyStatusEl.textContent = `${data.ready_user_ids.length} / 2 players ready.`;
    } else if (!iChoseLocation) {
      readyStatusEl.textContent = 'Pick your starting location.';
    } else {
      readyStatusEl.textContent = `Waiting for your opponent (${data.location_chosen_user_ids.length} / 2 ready to start)...`;
    }
  }

  if (isTableVisible) {
    document.getElementById('game-number').textContent = data.game_number;
    document.getElementById('turn-number').textContent = data.turn_number;
    document.getElementById('phase-name').textContent = data.phase || '—';
    document.getElementById('active-side').textContent = SIDE_LABELS[data.active_side] || '—';

    const isMyTurn = data.active_user_id === userId;
    const isActivatePhase = data.phase === 'Activate';
    const isDrawPhase = data.phase === 'Draw';

    // Activate and Draw are each a single explicit action (activate_force / draw_cards)
    // that automatically advances the phase/turn — Next Phase is only for the phases
    // that don't have their own action yet (Control, Deploy, Battle, Move).
    const hidePassPhase = isActivatePhase || isDrawPhase;
    passPhaseBtn.classList.toggle('d-none', hidePassPhase);
    passPhaseBtn.disabled = isGameOver || !isMyTurn || hidePassPhase;

    activateForceRow.classList.toggle('d-none', !isActivatePhase);
    activateForceBtn.disabled = isGameOver || !isMyTurn || !isActivatePhase;
    drawCardsRow.classList.toggle('d-none', !isDrawPhase);
    drawCardsBtn.disabled = isGameOver || !isMyTurn || !isDrawPhase;

    resignBtn.disabled = isGameOver;
    rematchBtn.disabled = !isGameOver || !data.room_is_full;
    phaseErrorEl.textContent = '';

    const opponentUserId = Object.keys(data.side_by_user_id).find(uid => Number(uid) !== userId);
    const opponentSide = opponentUserId ? data.side_by_user_id[opponentUserId] : null;
    const mySizes = data.pile_sizes_by_user_id[String(userId)];
    const oppSizes = opponentUserId ? data.pile_sizes_by_user_id[opponentUserId] : null;

    setPileBackClass(myPileStacks, mySide);
    setPileBackClass(oppPileStacks, opponentSide);

    if (mySizes) {
      document.getElementById('my-reserve-count').textContent = mySizes.reserve_deck;
      document.getElementById('my-force-count').textContent = mySizes.force_pile;
      document.getElementById('my-used-count').textContent = mySizes.used_pile;
      document.getElementById('my-lost-count').textContent = mySizes.lost_pile;
      activateForceInput.max = mySizes.max_force + 1;
    }
    if (oppSizes) {
      document.getElementById('opp-reserve-count').textContent = oppSizes.reserve_deck;
      document.getElementById('opp-force-count').textContent = oppSizes.force_pile;
      document.getElementById('opp-used-count').textContent = oppSizes.used_pile;
      document.getElementById('opp-lost-count').textContent = oppSizes.lost_pile;

      const backClass = SIDE_CARD_BACK_CLASS[opponentSide] || 'card-back-dark';
      opponentHandOverlay.innerHTML = Array.from({ length: oppSizes.hand })
        .map(() => `<div class="card-back ${backClass}"></div>`)
        .join('');
    }

    resultBanner.classList.toggle('d-none', !isGameOver);
    if (isGameOver) {
      const won = data.winner_user_id === userId;
      resultBanner.className = 'alert mt-0 mb-2 py-1 ' + (won ? 'alert-success' : 'alert-secondary');
      let text = won ? 'You win!' : 'You lost this game.';
      if (!data.room_is_full) {
        text += ' This room is open for a new challenger.';
      }
      resultBanner.textContent = text;
    }
  } else {
    myHand = [];
    handOverlay.innerHTML = '';
    opponentHandOverlay.innerHTML = '';
  }
}

readyBtn.addEventListener('click', () => {
  readyErrorEl.textContent = '';
  const deckId = readyDeckSelect.value;
  if (!deckId) return;
  socket.send(JSON.stringify({ type: 'ready', deck_id: deckId }));
});

confirmLocationBtn.addEventListener('click', () => {
  readyErrorEl.textContent = '';
  const locationId = locationSelect.value;
  if (!locationId) return;
  socket.send(JSON.stringify({ type: 'choose_starting_location', location_card_id: locationId }));
});

passPhaseBtn.addEventListener('click', () => {
  socket.send(JSON.stringify({ type: 'pass_phase' }));
});

activateForceBtn.addEventListener('click', () => {
  const count = parseInt(activateForceInput.value, 10) || 0;
  socket.send(JSON.stringify({ type: 'activate_force', count }));
});

drawCardsBtn.addEventListener('click', () => {
  const count = parseInt(drawCardsInput.value, 10) || 0;
  socket.send(JSON.stringify({ type: 'draw_cards', count }));
});

rematchBtn.addEventListener('click', () => {
  socket.send(JSON.stringify({ type: 'rematch' }));
});

document.getElementById('confirm-resign-btn').addEventListener('click', () => {
  socket.send(JSON.stringify({ type: 'resign' }));
});

document.getElementById('leave-room-btn').addEventListener('click', () => {
  document.getElementById('leave-room-body').textContent = currentStatus === 'in_progress'
    ? 'A game is in progress — leaving counts as resigning, and your opponent will win.'
    : 'You can rejoin later with the room code, as long as the slot is still open.';
});

document.getElementById('confirm-leave-btn').addEventListener('click', () => {
  navigateAfterClose = lobbyUrl;
  socket.send(JSON.stringify({ type: 'leave' }));
});

document.getElementById('confirm-close-room-btn').addEventListener('click', () => {
  navigateAfterClose = lobbyUrl;
  socket.send(JSON.stringify({ type: 'close_room' }));
});

chatToggleBtn.addEventListener('click', () => {
  isChatOpen = !isChatOpen;
  chatPanelBody.classList.toggle('d-none', !isChatOpen);
  chatWidget.classList.toggle('chat-collapsed', !isChatOpen);
  if (isChatOpen) {
    chatUnreadDot.classList.add('d-none');
    chatLog.scrollTop = chatLog.scrollHeight;
  }
});

document.getElementById('chat-form').addEventListener('submit', (e) => {
  e.preventDefault();
  const input = document.getElementById('chat-input');
  if (!input.value.trim()) return;
  socket.send(JSON.stringify({ type: 'chat', text: input.value.trim() }));
  input.value = '';
});
