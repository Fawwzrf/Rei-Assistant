/**
 * Expression Controller Module
 * Maps AI sentiment expressions to Live2D model parameters with smooth transitions.
 */

class ExpressionController {
  constructor() {
    this.model = null;
    this.currentExpression = 'neutral';
    this.targetParams = {};
    this.currentParams = {};
    this.transitionDuration = 500; // ms
    this.animationFrame = null;
    this.transitionStartTime = 0;
    this.startParams = {};

    // Default neutral parameters
    this.neutralParams = {
      ParamEyeLSmile: 0,
      ParamEyeRSmile: 0,
      ParamMouthForm: 0,
      ParamCheek: 0,
      ParamBrowLY: 0,
      ParamBrowRY: 0,
      ParamEyeLOpen: 1,
      ParamEyeROpen: 1,
      ParamMouthOpenY: 0,
      ParamBrowLAngle: 0,
      ParamBrowRAngle: 0,
      ParamEyeBallX: 0,
      ParamEyeBallY: 0,
    };

    // Local copy of expression definitions (fallback)
    this.expressions = {
      happy: {
        ParamEyeLSmile: 1.0,
        ParamEyeRSmile: 1.0,
        ParamMouthForm: 1.0,
        ParamCheek: 1.0,
      },
      sad: {
        ParamBrowLY: -1.0,
        ParamBrowRY: -1.0,
        ParamMouthForm: -0.5,
        ParamEyeLOpen: 0.5,
        ParamEyeROpen: 0.5,
      },
      surprised: {
        ParamEyeLOpen: 1.3,
        ParamEyeROpen: 1.3,
        ParamBrowLY: 1.0,
        ParamBrowRY: 1.0,
        ParamMouthOpenY: 0.8,
      },
      angry: {
        ParamBrowLAngle: -1.0,
        ParamBrowRAngle: -1.0,
        ParamMouthForm: -1.0,
        ParamEyeLOpen: 0.7,
        ParamEyeROpen: 0.7,
      },
      thinking: {
        ParamBrowLY: 0.5,
        ParamBrowRY: -0.3,
        ParamEyeBallX: -0.5,
        ParamEyeBallY: 0.3,
      },
      neutral: {},
    };
  }

  /**
   * Set the Live2D model to control.
   */
  setModel(model) {
    this.model = model;
    this._initCurrentParams();
  }

  /**
   * Initialize current params from neutral.
   */
  _initCurrentParams() {
    this.currentParams = { ...this.neutralParams };
  }

  /**
   * Apply an expression with smooth transition.
   * @param {string} expressionName - Name of the expression
   * @param {object} params - Optional params from backend (overrides local)
   * @param {number} duration - Transition duration in seconds
   */
  setExpression(expressionName, params = null, duration = 0.5) {
    if (this.currentExpression === expressionName && !params) return;

    this.currentExpression = expressionName;
    this.transitionDuration = duration * 1000;

    // Use backend-provided params or local fallback
    const targetExprParams = params || this.expressions[expressionName] || {};

    // Merge with neutral (unset params return to neutral)
    this.startParams = { ...this.currentParams };
    this.targetParams = { ...this.neutralParams, ...targetExprParams };
    this.transitionStartTime = performance.now();

    // Start transition animation
    this._cancelAnimation();
    this._animate();
  }

  /**
   * Set mouth open parameter for lip-sync.
   */
  setMouthOpen(value) {
    if (!this.model) return;
    
    try {
      const coreModel = this.model.internalModel?.coreModel;
      if (coreModel) {
        coreModel.setParameterValueById('ParamMouthOpenY', value);
      }
    } catch (e) {
      // Parameter might not exist on this model
    }
  }

  /**
   * Animation loop for smooth parameter transitions.
   */
  _animate() {
    const now = performance.now();
    const elapsed = now - this.transitionStartTime;
    const progress = Math.min(elapsed / this.transitionDuration, 1);

    // Ease-out cubic for natural feel
    const eased = 1 - Math.pow(1 - progress, 3);

    // Interpolate all parameters
    for (const [param, targetValue] of Object.entries(this.targetParams)) {
      const startValue = this.startParams[param] ?? this.neutralParams[param] ?? 0;
      const currentValue = startValue + (targetValue - startValue) * eased;
      this.currentParams[param] = currentValue;

      // Apply to Live2D model
      this._setParam(param, currentValue);
    }

    if (progress < 1) {
      this.animationFrame = requestAnimationFrame(() => this._animate());
    }
  }

  /**
   * Set a parameter on the Live2D model.
   */
  _setParam(paramId, value) {
    if (!this.model) return;

    try {
      const coreModel = this.model.internalModel?.coreModel;
      if (coreModel) {
        coreModel.setParameterValueById(paramId, value);
      }
    } catch (e) {
      // Silently ignore missing parameters
    }
  }

  /**
   * Cancel ongoing animation.
   */
  _cancelAnimation() {
    if (this.animationFrame) {
      cancelAnimationFrame(this.animationFrame);
      this.animationFrame = null;
    }
  }

  /**
   * Reset to neutral expression.
   */
  reset() {
    this.setExpression('neutral');
  }

  /**
   * Cleanup.
   */
  destroy() {
    this._cancelAnimation();
    this.model = null;
  }
}

export default ExpressionController;
