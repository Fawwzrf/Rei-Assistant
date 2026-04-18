/**
 * Live2D Manager Module
 * Handles loading and displaying Live2D models using PixiJS.
 * 
 * Note: This module provides a placeholder/fallback canvas rendering
 * when the Live2D Cubism SDK is not available. The full Live2D integration
 * requires the Cubism Core SDK (live2dcubismcore.min.js) and a compatible
 * PixiJS plugin like 'pixi-live2d-display'.
 */

class Live2DManager {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.app = null;
    this.model = null;
    this.isLoaded = false;
    this.useFallback = true; // Will be set to false when Live2D SDK is available

    // Fallback avatar state
    this._fallbackState = {
      eyeOpenL: 1,
      eyeOpenR: 1,
      mouthOpen: 0,
      expression: 'neutral',
      blinkTimer: 0,
      idleTimer: 0,
      breathPhase: 0,
    };
  }

  /**
   * Initialize the PixiJS application and load model.
   */
  async init() {
    try {
      console.log('[Live2D] WebGL SDK bypassed. Using beautiful canvas 2D animated avatar.');
      this.useFallback = true;
      this._initFallbackAvatar();
      this.isLoaded = true;
      console.log('[Live2D] Manager initialized');
    } catch (e) {
      console.error('[Live2D] Init failed:', e);
      this._initFallbackAvatar();
    }
  }

  /**
   * Attempt to load Live2D model with the SDK.
   */
  async _loadLive2DModel() {
    // Check if Cubism Core is available on window
    if (typeof window.Live2DCubismCore === 'undefined') {
      throw new Error('Live2DCubismCore not loaded');
    }

    // Dynamic import of Live2D display plugin (Cubism 4 only)
    const { Live2DModel } = await import('pixi-live2d-display/cubism4');

    const modelPath = '/live2d/hiyori/Hiyori.model3.json';
    this.model = await Live2DModel.from(modelPath);

    // Scale and position the model
    this.model.scale.set(0.25);
    this.model.anchor.set(0.5, 0.5);
    this.model.x = this.app.screen.width / 2;
    this.model.y = this.app.screen.height / 2;

    this.app.stage.addChild(this.model);
    this.useFallback = false;

    console.log('[Live2D] Model loaded successfully');
  }

  /**
   * Initialize a beautiful fallback avatar when Live2D SDK isn't available.
   */
  _initFallbackAvatar() {
    // Destroy Pixi JS application if it exists
    if (this.app) {
      this.app.destroy(false);
      this.app = null;
    }

    // Force clear any CSS background that might've been set
    this.canvas.style.backgroundColor = 'transparent';

    console.log('[Live2D] Fallback avatar active — using canvas rendering');
    this._startFallbackRendering();
  }

  /**
   * Start fallback canvas-based avatar rendering.
   */
  _startFallbackRendering() {
    const ctx = this.canvas.getContext('2d');
    if (!ctx) return;

    // Resize canvas
    const resize = () => {
      const parent = this.canvas.parentElement;
      this.canvas.width = parent.clientWidth * (window.devicePixelRatio || 1);
      this.canvas.height = parent.clientHeight * (window.devicePixelRatio || 1);
      ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
    };
    resize();
    window.addEventListener('resize', resize);

    const drawAvatar = (timestamp) => {
      const w = this.canvas.width / (window.devicePixelRatio || 1);
      const h = this.canvas.height / (window.devicePixelRatio || 1);
      const cx = w / 2;
      const cy = h / 2 - 20;

      ctx.clearRect(0, 0, w, h);

      const state = this._fallbackState;
      state.breathPhase += 0.02;
      state.blinkTimer += 1;
      state.idleTimer += 0.01;

      // Breathing animation
      const breathOffset = Math.sin(state.breathPhase) * 3;

      // Random blinking
      let eyeScale = 1;
      if (state.blinkTimer > 180 && state.blinkTimer < 190) {
        eyeScale = Math.max(0, 1 - Math.sin(((state.blinkTimer - 180) / 10) * Math.PI));
      }
      if (state.blinkTimer > 190) {
        state.blinkTimer = Math.random() * -60;
      }

      // Subtle idle sway
      const swayX = Math.sin(state.idleTimer * 0.5) * 5;
      const swayY = Math.cos(state.idleTimer * 0.7) * 3;

      // ─── Draw Body ─────────────────────────────────
      // Glow effect behind avatar
      const glow = ctx.createRadialGradient(cx, cy + 40, 30, cx, cy + 40, 200);
      glow.addColorStop(0, 'rgba(108, 99, 255, 0.15)');
      glow.addColorStop(1, 'rgba(108, 99, 255, 0)');
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, w, h);

      ctx.save();
      ctx.translate(cx + swayX, cy + breathOffset + swayY);

      // Hair (back)
      ctx.fillStyle = '#2D1B69';
      ctx.beginPath();
      ctx.ellipse(0, -35, 75, 85, 0, Math.PI, 0);
      ctx.fill();

      // Body / dress
      const dressGrad = ctx.createLinearGradient(-50, 60, 50, 180);
      dressGrad.addColorStop(0, '#4A3AFF');
      dressGrad.addColorStop(1, '#6C63FF');
      ctx.fillStyle = dressGrad;
      ctx.beginPath();
      ctx.moveTo(-35, 55);
      ctx.quadraticCurveTo(-55, 160, -45, 200);
      ctx.lineTo(45, 200);
      ctx.quadraticCurveTo(55, 160, 35, 55);
      ctx.closePath();
      ctx.fill();

      // Neck
      ctx.fillStyle = '#FFE0D0';
      ctx.fillRect(-10, 42, 20, 18);

      // Head
      const headGrad = ctx.createRadialGradient(-5, -10, 10, 0, -5, 55);
      headGrad.addColorStop(0, '#FFF0E6');
      headGrad.addColorStop(1, '#FFD8C4');
      ctx.fillStyle = headGrad;
      ctx.beginPath();
      ctx.ellipse(0, -5, 48, 52, 0, 0, Math.PI * 2);
      ctx.fill();

      // Hair (front)
      ctx.fillStyle = '#3D2B79';
      ctx.beginPath();
      ctx.ellipse(0, -38, 52, 30, 0, Math.PI, 0);
      ctx.fill();

      // Bangs
      ctx.fillStyle = '#3D2B79';
      ctx.beginPath();
      ctx.moveTo(-42, -25);
      ctx.quadraticCurveTo(-35, 0, -30, 5);
      ctx.lineTo(-20, -15);
      ctx.quadraticCurveTo(-15, -25, 0, -25);
      ctx.quadraticCurveTo(15, -25, 20, -15);
      ctx.lineTo(30, 5);
      ctx.quadraticCurveTo(35, 0, 42, -25);
      ctx.lineTo(42, -45);
      ctx.quadraticCurveTo(0, -60, -42, -45);
      ctx.closePath();
      ctx.fill();

      // Side hair
      ctx.fillStyle = '#2D1B69';
      ctx.beginPath();
      ctx.moveTo(-48, -15);
      ctx.quadraticCurveTo(-58, 30, -52, 90);
      ctx.quadraticCurveTo(-48, 60, -42, 20);
      ctx.closePath();
      ctx.fill();
      ctx.beginPath();
      ctx.moveTo(48, -15);
      ctx.quadraticCurveTo(58, 30, 52, 90);
      ctx.quadraticCurveTo(48, 60, 42, 20);
      ctx.closePath();
      ctx.fill();

      // Eyes
      const eyeY = -5;
      const eyeSpacing = 18;

      // Eye whites
      ctx.fillStyle = 'white';
      ctx.beginPath();
      ctx.ellipse(-eyeSpacing, eyeY, 10, 7 * eyeScale, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.ellipse(eyeSpacing, eyeY, 10, 7 * eyeScale, 0, 0, Math.PI * 2);
      ctx.fill();

      if (eyeScale > 0.2) {
        // Irises
        const irisGrad = ctx.createRadialGradient(-eyeSpacing, eyeY, 1, -eyeSpacing, eyeY, 6);
        irisGrad.addColorStop(0, '#8B5CF6');
        irisGrad.addColorStop(0.7, '#6C63FF');
        irisGrad.addColorStop(1, '#4338CA');
        ctx.fillStyle = irisGrad;
        ctx.beginPath();
        ctx.ellipse(-eyeSpacing, eyeY, 6, 5.5 * eyeScale, 0, 0, Math.PI * 2);
        ctx.fill();

        const irisGrad2 = ctx.createRadialGradient(eyeSpacing, eyeY, 1, eyeSpacing, eyeY, 6);
        irisGrad2.addColorStop(0, '#8B5CF6');
        irisGrad2.addColorStop(0.7, '#6C63FF');
        irisGrad2.addColorStop(1, '#4338CA');
        ctx.fillStyle = irisGrad2;
        ctx.beginPath();
        ctx.ellipse(eyeSpacing, eyeY, 6, 5.5 * eyeScale, 0, 0, Math.PI * 2);
        ctx.fill();

        // Pupils
        ctx.fillStyle = '#1E1040';
        ctx.beginPath();
        ctx.ellipse(-eyeSpacing, eyeY, 3, 3 * eyeScale, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.beginPath();
        ctx.ellipse(eyeSpacing, eyeY, 3, 3 * eyeScale, 0, 0, Math.PI * 2);
        ctx.fill();

        // Eye highlights
        ctx.fillStyle = 'rgba(255,255,255,0.9)';
        ctx.beginPath();
        ctx.ellipse(-eyeSpacing - 2, eyeY - 2, 2, 1.5 * eyeScale, -0.3, 0, Math.PI * 2);
        ctx.fill();
        ctx.beginPath();
        ctx.ellipse(eyeSpacing - 2, eyeY - 2, 2, 1.5 * eyeScale, -0.3, 0, Math.PI * 2);
        ctx.fill();
      }

      // Expression-based features
      const expr = state.expression;

      // Blush (happy/neutral)
      if (expr === 'happy' || expr === 'neutral') {
        ctx.fillStyle = 'rgba(255, 130, 150, 0.2)';
        ctx.beginPath();
        ctx.ellipse(-25, 12, 10, 5, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.beginPath();
        ctx.ellipse(25, 12, 10, 5, 0, 0, Math.PI * 2);
        ctx.fill();
      }

      // Mouth
      const mouthY = 18;
      const mouthOpen = state.mouthOpen;
      ctx.strokeStyle = '#D4726A';
      ctx.lineWidth = 2;
      ctx.lineCap = 'round';

      if (mouthOpen > 0.1) {
        // Open mouth
        ctx.fillStyle = '#8B3A3A';
        ctx.beginPath();
        ctx.ellipse(0, mouthY, 8, 4 + mouthOpen * 8, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#D4726A';
        ctx.stroke();
      } else if (expr === 'happy') {
        // Happy smile
        ctx.beginPath();
        ctx.arc(0, mouthY - 3, 10, 0.1 * Math.PI, 0.9 * Math.PI);
        ctx.stroke();
      } else if (expr === 'sad') {
        // Sad frown
        ctx.beginPath();
        ctx.arc(0, mouthY + 8, 10, 1.1 * Math.PI, 1.9 * Math.PI);
        ctx.stroke();
      } else {
        // Neutral small smile
        ctx.beginPath();
        ctx.arc(0, mouthY - 2, 7, 0.15 * Math.PI, 0.85 * Math.PI);
        ctx.stroke();
      }

      // Eyebrows
      ctx.strokeStyle = '#3D2B79';
      ctx.lineWidth = 2.5;
      const browY = -20;

      if (expr === 'surprised') {
        ctx.beginPath();
        ctx.arc(-eyeSpacing, browY - 5, 8, Math.PI * 1.1, Math.PI * 1.9);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(eyeSpacing, browY - 5, 8, Math.PI * 1.1, Math.PI * 1.9);
        ctx.stroke();
      } else if (expr === 'angry') {
        ctx.beginPath();
        ctx.moveTo(-eyeSpacing - 8, browY - 2);
        ctx.lineTo(-eyeSpacing + 8, browY + 3);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(eyeSpacing + 8, browY - 2);
        ctx.lineTo(eyeSpacing - 8, browY + 3);
        ctx.stroke();
      } else if (expr === 'sad') {
        ctx.beginPath();
        ctx.moveTo(-eyeSpacing - 8, browY + 2);
        ctx.lineTo(-eyeSpacing + 8, browY - 2);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(eyeSpacing + 8, browY + 2);
        ctx.lineTo(eyeSpacing - 8, browY - 2);
        ctx.stroke();
      } else {
        ctx.beginPath();
        ctx.moveTo(-eyeSpacing - 8, browY);
        ctx.quadraticCurveTo(-eyeSpacing, browY - 3, -eyeSpacing + 8, browY);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(eyeSpacing - 8, browY);
        ctx.quadraticCurveTo(eyeSpacing, browY - 3, eyeSpacing + 8, browY);
        ctx.stroke();
      }

      ctx.restore();

      // Name label below avatar
      ctx.fillStyle = 'rgba(108, 99, 255, 0.8)';
      ctx.font = '600 16px Outfit, Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('Rei', cx + swayX, cy + 230 + breathOffset);

      ctx.fillStyle = 'rgba(155, 155, 184, 0.6)';
      ctx.font = '400 11px Inter, sans-serif';
      ctx.fillText('AI Assistant', cx + swayX, cy + 248 + breathOffset);

      this._fallbackAnimFrame = requestAnimationFrame(drawAvatar);
    };

    drawAvatar(0);
  }

  /**
   * Update loop (for Live2D model).
   */
  _update(ticker) {
    if (this.model && !this.useFallback) {
      // Live2D model update handled by the plugin
    }
  }

  /**
   * Set expression on the model.
   */
  setExpression(expressionName) {
    if (this.useFallback) {
      this._fallbackState.expression = expressionName;
    }
  }

  /**
   * Set mouth open value for lip-sync.
   */
  setMouthOpen(value) {
    if (this.useFallback) {
      this._fallbackState.mouthOpen = value;
    }
  }

  /**
   * Get the Live2D model (for expression controller).
   */
  getModel() {
    return this.model;
  }

  /**
   * Cleanup.
   */
  destroy() {
    if (this._fallbackAnimFrame) {
      cancelAnimationFrame(this._fallbackAnimFrame);
    }
    if (this.app) {
      this.app.destroy(true);
    }
  }
}

export default Live2DManager;
