class Sprite {
  // Just handle the basic animation render.
  constructor({
    position,
    mirror = false,
    offset = { x: 0, y: 0 },
    imageSrc,
    scale = 1,
    totalFrames = 1,
  }) {
    this.position = position;
    this.mirror = mirror;
    this.height = 150;
    this.width = 50;
    this.image = new Image();
    this.image.src = imageSrc;
    this.scale = scale;
    this.totalFrames = totalFrames;
    this.currentFrame = 0;
    this.framesElapsed = 0;
    this.framesHold = 5;
    this.offset = offset;
  }

  draw() {
    canvas2dContext.drawImage(
      this.image,
      this.currentFrame * (this.image.width / this.totalFrames),
      0,
      this.image.width / this.totalFrames,
      this.image.height,
      this.position.x - this.offset.x,
      this.position.y - this.offset.y,
      (this.image.width / this.totalFrames) * this.scale,
      this.image.height * this.scale
    );
  }

  animateFrames() {
    // Render image frame from left to right
    this.framesElapsed++;
    if (this.framesElapsed % this.framesHold === 0) {
      if (this.currentFrame < this.totalFrames - 1) {
        this.currentFrame++;
      } else {
        this.currentFrame = 0;
      }
    }
  }

  update() {
    this.draw();
    this.animateFrames();
  }
}

class Fighter extends Sprite {
  constructor({
    position,
    mirror = false,
    velocity,
    color = "red",
    offset = { x: 0, y: 0 },
    imageSrc,
    scale = 1,
    totalFrames = 1,
    sprites,
    attackBox = {
      offset: {},
      width: undefined,
      height: undefined,
    },
  }) {
    // Call the constructor of the parent class
    super({
      position,
      mirror,
      offset,
      imageSrc,
      scale,
      totalFrames,
    });

    this.velocity = velocity;
    this.color = color;
    this.height = 150;
    this.width = 50;
    this.lastKey;
    this.isAttacking = false;
    this.health = 100;
    this.dead = false;
    this.attackBox = {
      position: {
        x: this.position.x,
        y: this.position.y,
      },
      offset: attackBox.offset,
      width: attackBox.width,
      height: attackBox.height,
    };
    this.currentFrame = 0;
    this.framesElapsed = 0;
    this.framesHold = 5;
    this.sprites = sprites;

    for (const sprite in this.sprites) {
      sprites[sprite].image = new Image();
      sprites[sprite].image.src = sprites[sprite].imageSrc;
    }
  }

  update() {
    this.draw();
    if (!this.dead) {
      this.animateFrames();
    }

    this.attackBox.position.x = this.position.x + this.attackBox.offset.x;
    this.attackBox.position.y = this.position.y + this.attackBox.offset.y;
    // // attack box for debugging
    // canvas2dContext.fillRect(
    //   this.attackBox.position.x,
    //   this.attackBox.position.y,
    //   this.attackBox.width,
    //   this.attackBox.height
    // );

    this.position.x += this.velocity.x;
    this.position.y += this.velocity.y;

    // Fitting to the ground and gravity feature.
    if (this.position.y + this.height + this.velocity.y >= canvas.height) {
      this.velocity.y = 0;
      this.position.y = 618; // Fixed to ground, minimize the duration.
    } else {
      this.velocity.y += gravity;
    }
  }

  attack() {
    this.switchSprite("attack");
    this.isAttacking = true;
  }

  takeHit() {
    this.health -= 20;
    if (this.health <= 0) {
      this.switchSprite("death");
    } else {
      this.switchSprite("takeHit");
    }
  }

  switchSprite(sprite) {
    if (this.image === this.sprites.death.image) {
      // death will overwrite others animate
      if (this.currentFrame === this.sprites.death.totalFrames - 1) {
        this.dead = true;
      }
      return;
    }
    if (
      this.image === this.sprites.attack.image &&
      this.currentFrame < this.sprites.attack.totalFrames - 1
    ) {
      // attack will overwrite others animate
      return;
    }
    if (
      this.image === this.sprites.takeHit.image &&
      this.currentFrame < this.sprites.takeHit.totalFrames - 1
    ) {
      // takeHit will overwrite others animate
      return;
    }

    switch (sprite) {
      case "idle":
        if (this.image !== this.sprites.idle.image) {
          this.image = this.sprites.idle.image;
          this.totalFrames = this.sprites.idle.totalFrames;
          this.currentFrame = 0;
        }
        break;
      case "run":
        if (this.image !== this.sprites.run.image) {
          this.image = this.sprites.run.image;
          this.totalFrames = this.sprites.run.totalFrames;
          this.currentFrame = 0;
        }
        break;
      case "jump":
        if (this.image !== this.sprites.jump.image) {
          this.image = this.sprites.jump.image;
          this.totalFrames = this.sprites.jump.totalFrames;
          this.currentFrame = 0;
        }
        break;
      case "fall":
        if (this.image !== this.sprites.fall.image) {
          this.image = this.sprites.fall.image;
          this.totalFrames = this.sprites.fall.totalFrames;
          this.currentFrame = 0;
        }
        break;
      case "attack":
        if (this.image !== this.sprites.attack.image) {
          this.image = this.sprites.attack.image;
          this.totalFrames = this.sprites.attack.totalFrames;
          this.currentFrame = 0;
        }
        break;
      case "takeHit":
        if (this.image !== this.sprites.takeHit.image) {
          this.image = this.sprites.takeHit.image;
          this.totalFrames = this.sprites.takeHit.totalFrames;
          this.currentFrame = 0;
        }
        break;
      case "death":
        if (this.image !== this.sprites.death.image) {
          this.image = this.sprites.death.image;
          this.totalFrames = this.sprites.death.totalFrames;
          this.currentFrame = 0;
        }
        break;
      default:
        break;
    }
  }
}

class CPUController {
  constructor(fighter, target) {
    this.version = "4.1-PREDICTIVE"; // Added predictive positioning
    console.log(`🤖 CPU Controller ${this.version} initialized`);
    
    this.fighter = fighter;
    this.target = target;
    this.lastAction = Date.now();
    this.lastAttack = Date.now();
    this.difficulty = 'easy';
    this.currentState = 'approaching';
    this.stateTimer = Date.now();
    
    // Logging system
    this.enableLogging = true;
    this.logCount = 0;
    this.maxLogs = 50;
    this.logBuffer = [];
    this.lastLogWrite = Date.now();
    this.logWriteInterval = 5000;
    
    // SIMPLE AI parameters - with predictive positioning
    this.behaviors = {
      easy: {
        reactionTime: 800,
        moveSpeed: 1.5,
        attackRange: 100, // Increased for better positioning
        retreatRange: 140,
        attackCooldown: 2000
      },
      medium: {
        reactionTime: 600,
        moveSpeed: 2.5,
        attackRange: 110, // Increased for better positioning
        retreatRange: 150,
        attackCooldown: 1500
      },
      hard: {
        reactionTime: 400,
        moveSpeed: 4,
        attackRange: 120, // Increased for better positioning
        retreatRange: 160,
        attackCooldown: 1000
      }
    };
  }

  getDistanceToTarget() {
    return Math.abs(this.fighter.position.x - this.target.position.x);
  }

  shouldAct() {
    const behavior = this.behaviors[this.difficulty];
    return Date.now() - this.lastAction > behavior.reactionTime;
  }

  canAttack() {
    const behavior = this.behaviors[this.difficulty];
    return Date.now() - this.lastAttack > behavior.attackCooldown;
  }

  log(action, reason, data = {}) {
    if (this.enableLogging && this.logCount < this.maxLogs) {
      const distance = this.getDistanceToTarget();
      const timestamp = new Date().toISOString();
      const logEntry = {
        timestamp,
        action,
        reason,
        distance: Math.round(distance),
        cpuPos: Math.round(this.fighter.position.x),
        cpuVel: Math.round(this.fighter.velocity.x * 10) / 10,
        playerPos: Math.round(this.target.position.x),
        state: this.currentState,
        ...data
      };
      
      this.logBuffer.push(logEntry);
      console.log(`🤖 [${this.difficulty.toUpperCase()}] ${action}: ${reason} | Dist: ${Math.round(distance)} | Vel: ${logEntry.cpuVel}`);
      this.logCount++;
      
      if (Date.now() - this.lastLogWrite > this.logWriteInterval) {
        this.writeLogsToFile();
      }
    }
  }

  writeLogsToFile() {
    if (this.logBuffer.length > 0) {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const logContent = this.logBuffer.map(entry => 
        `${entry.timestamp} | ${entry.action} | ${entry.reason} | Distance: ${entry.distance} | CPU: pos=${entry.cpuPos}, vel=${entry.cpuVel} | Player: pos=${entry.playerPos} | State: ${entry.state}`
      ).join('\n');
      
      const blob = new Blob([logContent], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cpu-log-${timestamp}.txt`;
      a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      this.logBuffer = [];
      this.lastLogWrite = Date.now();
    }
  }

  update() {
    if (this.fighter.dead || this.target.dead) return;

    const behavior = this.behaviors[this.difficulty];
    const distance = this.getDistanceToTarget();
    
    // PREDICTIVE POSITIONING - account for current velocity and reaction time
    const velocityX = this.fighter.velocity.x;
    const futurePositionX = this.fighter.position.x + (velocityX * behavior.reactionTime / 16.67); // 16.67ms per frame at 60fps
    const predictedDistance = Math.abs(futurePositionX - this.target.position.x);

    // Simple state machine - only make decisions when reaction time allows
    if (this.shouldAct()) {
      // EMERGENCY: Player attacking and very close
      if (this.target.isAttacking && distance < 60) {
        this.log("EMERGENCY_DODGE", "Player attacking too close - dodge!");
        this.jump();
        this.moveAway(behavior.moveSpeed * 2);
        this.currentState = 'retreating';
      }
      // ATTACK: Use predicted distance to avoid overshooting
      else if (predictedDistance <= behavior.attackRange && this.canAttack()) {
        this.log("ATTACK", `In range - attacking now! (predicted: ${Math.round(predictedDistance)})`);
        this.stop();
        this.attack();
        this.currentState = 'retreating';
      }
      // SLOW DOWN: If we're approaching and will overshoot, slow down early
      else if (distance > behavior.attackRange && predictedDistance <= behavior.attackRange * 1.2) {
        this.log("SLOW_APPROACH", `Slowing down to avoid overshoot (current: ${Math.round(distance)}, predicted: ${Math.round(predictedDistance)})`);
        this.moveToward(behavior.moveSpeed * 0.3); // Much slower
        this.currentState = 'approaching';
      }
      // RETREAT: Too close to player
      else if (distance < behavior.retreatRange) {
        this.log("RETREAT", "Too close - backing away");
        this.moveAway(behavior.moveSpeed);
        this.currentState = 'retreating';
      }
      // APPROACH: Too far from player
      else {
        this.log("APPROACH", "Moving toward player");
        this.moveToward(behavior.moveSpeed);
        this.currentState = 'approaching';
      }
      
      this.lastAction = Date.now();
    }

    this.updateSprite();
    
    if (Date.now() - this.lastLogWrite > this.logWriteInterval) {
      this.writeLogsToFile();
    }
  }

  // SIMPLE movement functions - with distance checks
  moveToward(speed) {
    const oldVel = this.fighter.velocity.x;
    const distance = this.getDistanceToTarget();
    
    // SAFETY: Don't move if already very close to avoid overshooting
    if (distance < 60) {
      this.stop();
      return;
    }
    
    if (this.fighter.position.x > this.target.position.x) {
      this.fighter.velocity.x = -speed;
      this.fighter.lastKey = "ArrowLeft";
    } else {
      this.fighter.velocity.x = speed;
      this.fighter.lastKey = "ArrowRight";
    }
    
    if (Math.abs(this.fighter.velocity.x - oldVel) > 0.1) {
      this.log("MOVE", `Velocity: ${oldVel.toFixed(1)} -> ${this.fighter.velocity.x.toFixed(1)}`);
    }
  }

  moveAway(speed) {
    const oldVel = this.fighter.velocity.x;
    
    if (this.fighter.position.x > this.target.position.x) {
      this.fighter.velocity.x = speed;
      this.fighter.lastKey = "ArrowLeft"; // Still face the player
    } else {
      this.fighter.velocity.x = -speed;
      this.fighter.lastKey = "ArrowRight"; // Still face the player
    }
    
    if (Math.abs(this.fighter.velocity.x - oldVel) > 0.1) {
      this.log("MOVE", `Velocity: ${oldVel.toFixed(1)} -> ${this.fighter.velocity.x.toFixed(1)}`);
    }
  }

  stop() {
    const oldVel = this.fighter.velocity.x;
    this.fighter.velocity.x = 0;
    
    if (Math.abs(oldVel) > 0.1) {
      this.log("STOP", `Velocity: ${oldVel.toFixed(1)} -> 0.0`);
    }
  }

  attack() {
    this.fighter.attack();
    this.lastAttack = Date.now();
  }

  jump() {
    if (this.fighter.position.y >= 618) {
      this.fighter.velocity.y = -20;
    }
  }

  updateSprite() {
    if (this.fighter.velocity.x !== 0) {
      this.fighter.switchSprite("run");
    } else {
      this.fighter.switchSprite("idle");
    }

    if (this.fighter.velocity.y < 0) {
      this.fighter.switchSprite("jump");
    } else if (this.fighter.velocity.y > 0) {
      this.fighter.switchSprite("fall");
    }
  }

  setDifficulty(difficulty) {
    if (this.behaviors[difficulty]) {
      this.difficulty = difficulty;
      this.log("DIFFICULTY", `Changed to ${difficulty}`);
    }
  }

  toggleLogging() {
    this.enableLogging = !this.enableLogging;
    console.log(`🤖 CPU Logging ${this.enableLogging ? 'ENABLED' : 'DISABLED'}`);
    return this.enableLogging;
  }

  resetLogCounter() {
    this.logCount = 0;
  }

  saveLogsNow() {
    this.writeLogsToFile();
  }
}
