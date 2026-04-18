/**
 * Chat Manager Module
 * Handles chat UI rendering, message display, and user input.
 */

class ChatManager {
  constructor() {
    this.messagesContainer = document.getElementById('chatMessages');
    this.chatInput = document.getElementById('chatInput');
    this.btnSend = document.getElementById('btnSend');
    this.btnReset = document.getElementById('btnResetChat');
    this.currentStreamBubble = null;
    this.currentStreamText = '';
    this.isStreaming = false;

    this._setupInputHandlers();
  }

  /**
   * Set up input event handlers.
   */
  _setupInputHandlers() {
    // Auto-resize textarea
    this.chatInput.addEventListener('input', () => {
      this.chatInput.style.height = 'auto';
      this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 120) + 'px';
    });

    // Enter to send (Shift+Enter for newline)
    this.chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this._onSend();
      }
    });

    // Send button
    this.btnSend.addEventListener('click', () => this._onSend());

    // Reset button
    this.btnReset.addEventListener('click', () => {
      if (this.onReset) this.onReset();
      this.clearMessages();
      this.addAssistantMessage(
        'Percakapan direset! Halo lagi! 👋 Ada yang bisa aku bantu?'
      );
    });
  }

  /**
   * Handle send action.
   */
  _onSend() {
    const text = this.chatInput.value.trim();
    if (!text || this.isStreaming) return;

    this.addUserMessage(text);
    this.chatInput.value = '';
    this.chatInput.style.height = 'auto';

    if (this.onSendMessage) {
      this.onSendMessage(text);
    }
  }

  /**
   * Add a user message bubble.
   */
  addUserMessage(text) {
    const msgEl = this._createMessageElement('user', text);
    this.messagesContainer.appendChild(msgEl);
    this._scrollToBottom();
  }

  /**
   * Add a complete assistant message.
   */
  addAssistantMessage(text) {
    const msgEl = this._createMessageElement('assistant', text);
    this.messagesContainer.appendChild(msgEl);
    this._scrollToBottom();
  }

  /**
   * Start streaming an assistant response.
   */
  startStream() {
    this.isStreaming = true;
    this.currentStreamText = '';
    this.btnSend.disabled = true;

    const msgEl = this._createMessageElement('assistant', '');
    const bubble = msgEl.querySelector('.message-bubble');
    bubble.classList.add('streaming');
    this.currentStreamBubble = bubble;

    this.messagesContainer.appendChild(msgEl);
    this._scrollToBottom();
  }

  /**
   * Append a token to the current stream.
   */
  appendToken(token) {
    if (!this.currentStreamBubble) return;

    this.currentStreamText += token;
    this.currentStreamBubble.innerHTML = this._formatText(this.currentStreamText);
    this._scrollToBottom();
  }

  /**
   * End the current stream.
   */
  endStream(finalText) {
    if (this.currentStreamBubble) {
      this.currentStreamBubble.classList.remove('streaming');
      if (finalText) {
        this.currentStreamBubble.innerHTML = this._formatText(finalText);
      }
    }

    this.currentStreamBubble = null;
    this.currentStreamText = '';
    this.isStreaming = false;
    this.btnSend.disabled = false;
    this._scrollToBottom();
  }

  /**
   * Add a system/error message.
   */
  addSystemMessage(text, type = 'info') {
    const el = document.createElement('div');
    el.className = `message message--system message--${type}`;
    el.innerHTML = `<div class="system-msg">${text}</div>`;
    this.messagesContainer.appendChild(el);
    this._scrollToBottom();
  }

  /**
   * Clear all messages except the welcome.
   */
  clearMessages() {
    this.messagesContainer.innerHTML = '';
  }

  /**
   * Create a message DOM element.
   */
  _createMessageElement(role, text) {
    const msg = document.createElement('div');
    msg.className = `message message--${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'user' ? 'U' : 'R';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = this._formatText(text);

    msg.appendChild(avatar);
    msg.appendChild(bubble);

    return msg;
  }

  /**
   * Format text with basic markdown-like formatting.
   */
  _formatText(text) {
    if (!text) return '';

    return text
      // Bold
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      // Italic
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      // Code inline
      .replace(/`(.*?)`/g, '<code>$1</code>')
      // Line breaks
      .replace(/\n/g, '<br>');
  }

  /**
   * Auto-scroll to the newest message.
   */
  _scrollToBottom() {
    requestAnimationFrame(() => {
      this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    });
  }

  // Callbacks (set by main.js)
  onSendMessage = null;
  onReset = null;
}

export default ChatManager;
