const lobbyUrl = document.currentScript.dataset.lobbyUrl;

const roomCode = JSON.parse(document.getElementById('room-code').textContent);
const userId = JSON.parse(document.getElementById('user-id').textContent);
const lightDecks = JSON.parse(document.getElementById('light-decks').textContent);
const darkDecks = JSON.parse(document.getElementById('dark-decks').textContent);
const SIDE_LABELS = { D: 'Dark Side', L: 'Light Side' };

const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const socket = new WebSocket(`${protocol}//${window.location.host}/ws/game/${roomCode}/`);

const statusEl = document.getElementById('connection-status');
const playersConnectedEl = document.getElementById('players-connected');
const waitingPanel = document.getElementById('waiting-panel');
const readyPanel = document.getElementById('ready-panel');
const gamePanel = document.getElementById('game-panel');
const readyDeckSelect = document.getElementById('ready-deck-select');
const readyBtn = document.getElementById('ready-btn');
const locationSelectRow = document.getElementById('location-select-row');
const locationSelect = document.getElementById('location-select');
const confirmLocationBtn = document.getElementById('confirm-location-btn');
const readyStatusEl = document.getElementById('ready-status');
const readyErrorEl = document.getElementById('ready-error');
const passPhaseBtn = document.getElementById('pass-phase-btn');
const resignBtn = document.getElementById('resign-btn');
const rematchBtn = document.getElementById('rematch-btn');
const resultBanner = document.getElementById('game-result-banner');
const phaseErrorEl = document.getElementById('phase-error');
const chatLog = document.getElementById('chat-log');
const closeRoomBtn = document.getElementById('close-room-btn');

let currentStatus = null;

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
  } else if (data.type === 'chat') {
    const line = document.createElement('div');
    line.textContent = `${data.username}: ${data.text}`;
    chatLog.appendChild(line);
    chatLog.scrollTop = chatLog.scrollHeight;
  }
});

// Keeps idle-turn detection ticking over even if the waiting player never sends anything.
setInterval(() => {
  if (socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'ping' }));
  }
}, 30000);

function renderState(data) {
  playersConnectedEl.textContent = `${data.connected_user_ids.length} / 2 players connected`;
  currentStatus = data.status;

  const isInProgress = data.status === 'in_progress';
  const isGameOver = data.status === 'game_over';

  const isCreator = data.creator_user_id === userId;
  closeRoomBtn.classList.toggle('d-none', !isCreator || isInProgress);

  waitingPanel.classList.toggle('d-none', data.status !== 'waiting_for_player');
  readyPanel.classList.toggle('d-none', data.status !== 'awaiting_ready');
  gamePanel.classList.toggle('d-none', !isInProgress && !isGameOver);

  if (data.status === 'awaiting_ready') {
    const mySide = data.side_by_user_id[String(userId)];
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

  if (isInProgress || isGameOver) {
    document.getElementById('game-number').textContent = data.game_number;
    document.getElementById('turn-number').textContent = data.turn_number;
    document.getElementById('phase-name').textContent = data.phase || '—';
    document.getElementById('active-side').textContent = SIDE_LABELS[data.active_side] || '—';
    passPhaseBtn.disabled = isGameOver || data.active_user_id !== userId;
    resignBtn.disabled = isGameOver;
    rematchBtn.disabled = !isGameOver || !data.room_is_full;
    phaseErrorEl.textContent = '';

    resultBanner.classList.toggle('d-none', !isGameOver);
    if (isGameOver) {
      const won = data.winner_user_id === userId;
      resultBanner.className = 'alert mt-0 mb-3 ' + (won ? 'alert-success' : 'alert-secondary');
      let text = won ? 'You win!' : 'You lost this game.';
      if (!data.room_is_full) {
        text += ' This room is open for a new challenger — share the code again to play another game.';
      }
      resultBanner.textContent = text;
    }
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

document.getElementById('chat-form').addEventListener('submit', (e) => {
  e.preventDefault();
  const input = document.getElementById('chat-input');
  if (!input.value.trim()) return;
  socket.send(JSON.stringify({ type: 'chat', text: input.value.trim() }));
  input.value = '';
});
