/**
 * Gemma-Aura — Main Entry Point
 * Initializes all modules and orchestrates the AI assistant.
 */

import WebSocketClient from './modules/websocket-client.js';
import ChatManager from './modules/chat-manager.js';
import Live2DManager from './modules/live2d-manager.js';
import ExpressionController from './modules/expression-controller.js';
import AudioRecorder from './modules/audio-recorder.js';
import AudioPlayer from './modules/audio-player.js';

// ─── Initialize Modules ──────────────────────────────────────────────────
const ws = new WebSocketClient();
const chat = new ChatManager();
const live2d = new Live2DManager('live2dCanvas');
const expression = new ExpressionController();
const recorder = new AudioRecorder();
const player = new AudioPlayer();

// ─── DOM References ──────────────────────────────────────────────────────
const connectionStatus = document.getElementById('connectionStatus');
const avatarStatus = document.getElementById('avatarStatus');
const statusText = document.getElementById('statusText');
const btnMic = document.getElementById('btnMic');
const thinkingOverlay = document.getElementById('thinkingOverlay');

// ─── Titlebar Controls ───────────────────────────────────────────────────
document.getElementById('btnMinimize')?.addEventListener('click', () => {
  window.electronAPI?.minimize();
});
document.getElementById('btnMaximize')?.addEventListener('click', () => {
  window.electronAPI?.maximize();
});
document.getElementById('btnClose')?.addEventListener('click', () => {
  window.electronAPI?.close();
});

// ─── WebSocket Event Handlers ────────────────────────────────────────────
ws.on('connected', () => {
  connectionStatus.textContent = 'Connected';
  connectionStatus.classList.add('connected');
  setAvatarState('idle');
});

ws.on('disconnected', () => {
  connectionStatus.textContent = 'Disconnected';
  connectionStatus.classList.remove('connected');
  setAvatarState('error');
});

ws.on('error', (data) => {
  if (data?.message) {
    chat.addSystemMessage(`Error: ${data.message}`, 'error');
  }
});

ws.on('token', (data) => {
  if (!chat.isStreaming) {
    chat.startStream();
  }
  
  if (data.text) {
    // Hide partial or full expression tags like [EXPR, [EXPRESSION:smile]
    // We use a regex that matches any part of an expression tag so it doesn't flicker on screen
    let textToDisplay = data.text;
    
    // If the token itself is just part of an expression bracket, we can accumulate it,
    // but the easiest way is to filter using the chat-manager's current string or simply
    // filter token-by-token. Since tokens can split `[EXPRESSION...`, we better keep track of state
    // But for a simple implementation, if token contains `[EXPRESSION:` or parts of it, we omit it.
    // Instead of doing stateful stripping here, we'll just append it and let chat manager format it.
    // Actually, `[EXPRESSION:xyz]` comes through tokens. We'll strip it in the formatter.
    chat.appendToken(data.text);
  }
});

ws.on('sentence', (data) => {
  if (data.audio) {
    // Only enqueue the audio for playback. 
    // The text has already been continuously displayed via token stream.
    player.enqueue(data.audio, null);
  }

  // Apply expression if the sentence dictates one
  if (data.expression && data.expression !== "neutral") {
    live2d.setExpression(data.expression);
    expression.setExpression(data.expression, {}, 0.5);
  }
});

ws.on('response_complete', (data) => {
  // Removed endStream here because the queue might still be playing out.
  // Thinking overlay is hidden to show we're speaking
  thinkingOverlay.hidden = true;

  if (data.expression) {
    // Final expression setter mapping
    live2d.setExpression(data.expression);
    expression.setExpression(
      data.expression,
      data.expression_params,
      data.transition_duration || 0.5
    );
  }
});

ws.on('audio_response', (data) => {
  // Legacy handler — audio now arrives chunked via 'sentence'.
});

ws.on('stt_result', (data) => {
  if (data.text) {
    chat.addUserMessage(data.text);
  }
});

ws.on('status', (data) => {
  setAvatarState(data.state);

  if (data.state === 'thinking') {
    thinkingOverlay.hidden = false;
  } else {
    thinkingOverlay.hidden = true;
  }
});

ws.on('max_reconnect', () => {
  connectionStatus.textContent = 'Offline';
  chat.addSystemMessage(
    '⚠️ Tidak dapat terhubung ke backend. Pastikan server berjalan.',
    'error'
  );
});

// ─── Chat Callbacks ──────────────────────────────────────────────────────
chat.onSendMessage = (text) => {
  ws.sendChat(text);
};

chat.onReset = () => {
  ws.resetConversation();
  player.stop();
  live2d.setExpression('neutral');
  chat.endStream('');
};

// ─── Audio / Mic Controls ────────────────────────────────────────────────
let micInitialized = false;

btnMic.addEventListener('mousedown', async () => {
  if (!micInitialized) {
    const ok = await recorder.init();
    if (!ok) {
      chat.addSystemMessage('🎤 Akses mikrofon ditolak.', 'error');
      return;
    }
    micInitialized = true;
  }

  recorder.startRecording();
  btnMic.classList.add('recording');
  setAvatarState('listening');
});

btnMic.addEventListener('mouseup', () => {
  if (recorder.isRecording) {
    recorder.stopRecording();
    btnMic.classList.remove('recording');
    setAvatarState('idle');
  }
});

btnMic.addEventListener('mouseleave', () => {
  if (recorder.isRecording) {
    recorder.stopRecording();
    btnMic.classList.remove('recording');
    setAvatarState('idle');
  }
});

recorder.onAudioReady = (base64Data) => {
  ws.sendAudio(base64Data);
};

// ─── Audio Player → Lip Sync & Text Sync ────────────────────────────────
player.onPlayStart = (text) => {
  if (text) chat.appendToken(text);
};

player.onAmplitude = (amplitude) => {
  live2d.setMouthOpen(amplitude);
  expression.setMouthOpen(amplitude);
};

player.onPlayEnd = () => {
  setAvatarState('idle');
  live2d.setMouthOpen(0);
  chat.endStream(); // End stream only when audio completely finishes
};

// ─── Status Helpers ──────────────────────────────────────────────────────
function setAvatarState(state) {
  // Remove old state classes
  avatarStatus.className = 'avatar-status';

  switch (state) {
    case 'idle':
      avatarStatus.classList.add('idle');
      statusText.textContent = 'Online';
      break;
    case 'thinking':
      avatarStatus.classList.add('thinking');
      statusText.textContent = 'Berpikir...';
      live2d.setExpression('thinking');
      break;
    case 'speaking':
      avatarStatus.classList.add('speaking');
      statusText.textContent = 'Berbicara...';
      break;
    case 'listening':
      avatarStatus.classList.add('listening');
      statusText.textContent = 'Mendengar...';
      break;
    case 'error':
      avatarStatus.classList.add('error');
      statusText.textContent = 'Offline';
      break;
    default:
      statusText.textContent = state;
  }
}

// ─── Initialize Everything ───────────────────────────────────────────────
async function init() {
  console.log('🌟 Gemma-Aura initializing...');

  // Initialize Live2D avatar
  await live2d.init();

  // Connect expression controller to model
  const model = live2d.getModel();
  if (model) {
    expression.setModel(model);
  }

  // Connect to backend
  ws.connect();

  console.log('✨ Gemma-Aura ready!');
}

init();
