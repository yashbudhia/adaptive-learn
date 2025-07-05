const canvas = document.querySelector("canvas");
canvas.width = 1366;
canvas.height = 768;

const canvas2dContext = canvas.getContext("2d");
canvas2dContext.fillRect(0, 0, canvas.width, canvas.height);

const gravity = 0.7;

// Game logging system
class GameLogger {
  constructor() {
    this.enablePlayerLogging = true;
    this.playerLogCount = 0;
    this.maxLogs = 50;
  }

  logPlayer(action, details = {}) {
    if (this.enablePlayerLogging && this.playerLogCount < this.maxLogs) {
      const playerState = {
        position: Math.round(player.position.x),
        velocityX: Math.round(player.velocity.x),
        velocityY: Math.round(player.velocity.y),
        health: player.health,
        attacking: player.isAttacking,
        onGround: player.position.y >= 618
      };
      
      console.log(`🎮 PLAYER | ${action}`, { state: playerState, ...details });
      this.playerLogCount++;
    }
  }

  togglePlayerLogging() {
    this.enablePlayerLogging = !this.enablePlayerLogging;
    console.log(`🎮 Player Logging ${this.enablePlayerLogging ? 'ENABLED' : 'DISABLED'}`);
    return this.enablePlayerLogging;
  }

  resetLogCounter() {
    this.playerLogCount = 0;
    console.log("🎮 Player Log counter reset");
  }
}

const gameLogger = new GameLogger();

const background = new Sprite({
  position: {
    x: 0,
    y: 0,
  },
  imageSrc: "./image/Hills.png",
});
const castle = new Sprite({
  position: {
    x: 1215,
    y: 540,
  },
  imageSrc: "./image/castle.png",
  totalFrames: 1,
});

const player = new Fighter({
  position: {
    x: 30,
    y: 0,
  },
  velocity: {
    x: 0,
    y: 10,
  },
  offset: {
    x: 150,
    y: 90,
  },
  imageSrc: "./image/player1/Idle.png",
  totalFrames: 11,
  scale: 2,
  sprites: {
    idle: {
      imageSrc: "./image/player1/Idle.png",
      totalFrames: 11,
    },
    run: {
      imageSrc: "./image/player1/Run.png",
      totalFrames: 8,
    },
    jump: {
      imageSrc: "./image/player1/Jump.png",
      totalFrames: 3,
    },
    fall: {
      imageSrc: "./image/player1/Fall.png",
      totalFrames: 3,
    },
    attack: {
      imageSrc: "./image/player1/Attack2.png",
      totalFrames: 7,
    },
    takeHit: {
      imageSrc: "./image/player1/Take Hit.png",
      totalFrames: 4,
    },
    death: {
      imageSrc: "./image/player1/Death.png",
      totalFrames: 11,
    },
  },
  attackBox: {
    offset: {
      x: 60,
      y: 30,
    },
    width: 130,
    height: 80,
  },
});
player.draw();

const enemy = new Fighter({
  position: {
    x: 1200,
    y: 500,
  },
  velocity: {
    x: 0,
    y: 0,
  },
  offset: {
    x: 150,
    y: 80,
  },
  imageSrc: "./image/player2/Idle.png",
  totalFrames: 10,
  scale: 2.2,
  sprites: {
    idle: {
      imageSrc: "./image/player2/Idle.png",
      totalFrames: 10,
    },
    run: {
      imageSrc: "./image/player2/Run.png",
      totalFrames: 8,
    },
    jump: {
      imageSrc: "./image/player2/Jump.png",
      totalFrames: 3,
    },
    fall: {
      imageSrc: "./image/player2/Fall.png",
      totalFrames: 3,
    },
    attack: {
      imageSrc: "./image/player2/Attack3.png",
      totalFrames: 8,
    },
    takeHit: {
      imageSrc: "./image/player2/Take hit.png",
      totalFrames: 3,
    },
    death: {
      imageSrc: "./image/player2/Death.png",
      totalFrames: 7,
    },
  },
  attackBox: {
    offset: {
      x: -140,
      y: 30,
    },
    width: 130,
    height: 80,
  },
});
enemy.draw();

// Initialize CPU controller for the enemy
const enemyCPU = new CPUController(enemy, player);

const keys = {
  a: {
    pressed: false,
  },
  d: {
    pressed: false,
  },
};

function rectangularCollision({ rectangule1, rectangule2 }) {
  return (
    rectangule1.attackBox.position.x + rectangule1.attackBox.width >=
      rectangule2.position.x &&
    rectangule1.attackBox.position.x <=
      rectangule2.position.x + rectangule2.width &&
    rectangule1.attackBox.position.y + rectangule1.attackBox.height >=
      rectangule2.position.y &&
    rectangule1.attackBox.position.y <=
      rectangule2.position.y + rectangule2.height
  );
}

function determineWinner({ player, enemy, startCountDown }) {
  clearInterval(startCountDown);
  document.querySelector(".dialog").style.display = "flex";
  if (player.health === enemy.health) {
    document.querySelector(".dialog").innerHTML = "Tie";
  } else if (player.health > enemy.health) {
    document.querySelector(".dialog").innerHTML = "Player Wins";
  } else if (player.health < enemy.health) {
    document.querySelector(".dialog").innerHTML = "CPU Wins";
  }
}

let timmer = 100;
const startCountDown = setInterval(() => {
  if (timmer > 0) {
    timmer--;
    document.querySelector(".timer").innerHTML = timmer;
  }
  if (timmer === 0) {
    determineWinner({ player, enemy, startCountDown });
  }
}, 1000);

function animate() {
  window.requestAnimationFrame(animate);
  canvas2dContext.fillStyle = "black";
  canvas2dContext.fillRect(0, 0, canvas.width, canvas.height);
  background.update();
  castle.update();
  // Let background be more transparent.
  canvas2dContext.fillStyle = "rgba(255, 255, 255, 0.1)";
  canvas2dContext.fillRect(0, 0, canvas.width, canvas.height);
  player.update();
  enemy.update();

  // player movement
  player.velocity.x = 0;
  if (keys.a.pressed && player.lastKey === "a") {
    player.velocity.x = -5;
    player.switchSprite("run");
  } else if (keys.d.pressed && player.lastKey === "d") {
    player.velocity.x = 5;
    player.switchSprite("run");
  } else {
    player.switchSprite("idle");
  }
  // jumping up to down
  if (player.velocity.y < 0) {
    player.switchSprite("jump");
  } else if (player.velocity.y > 0) {
    player.switchSprite("fall");
  }

  // Update CPU enemy behavior
  enemyCPU.update();

  //detect for attack collision
  if (
    rectangularCollision({ rectangule1: player, rectangule2: enemy }) &&
    player.isAttacking &&
    player.currentFrame === 4
  ) {
    player.isAttacking = false; // one attack per count
    console.log("🎯 HIT! Player hit CPU");
    gameLogger.logPlayer("HIT_SUCCESS", { damage: 20, enemyHealth: enemy.health - 20 });
    enemy.takeHit();
    // document.querySelector(
    //   "div.player2 > .health"
    // ).style.width = `${enemy.health}%`;
    gsap.to("div.player2 > .health", {
      width: enemy.health + "%",
    });
  }
  // play attack miss
  if (player.isAttacking && player.currentFrame === 4) {
    player.isAttacking = false;
    gameLogger.logPlayer("ATTACK_MISS", { reason: "No collision detected" });
  }
  if (
    rectangularCollision({ rectangule1: enemy, rectangule2: player }) &&
    enemy.isAttacking &&
    enemy.currentFrame === 4
  ) {
    enemy.isAttacking = false; // one attack per count
    console.log("💀 HIT! CPU hit Player");
    player.takeHit();
    // document.querySelector(
    //   "div.player1 > .health"
    // ).style.width = `${player.health}%`;
    gsap.to("div.player1 > .health", {
      width: player.health + "%",
    });
  }
  // enemy attack miss
  if (enemy.isAttacking && enemy.currentFrame === 4) {
    enemy.isAttacking = false;
  }

  if (player.health <= 0 || enemy.health <= 0) {
    determineWinner({ player, enemy, startCountDown });
  }
}
animate();

window.addEventListener("keydown", (event) => {
  console.log(event.key);
  // player movement
  if (!player.dead) {
    switch (event.key) {
      case "a":
        keys.a.pressed = true;
        player.lastKey = "a";
        gameLogger.logPlayer("MOVE_LEFT", { key: "a" });
        break;
      case "d":
        keys.d.pressed = true;
        player.lastKey = "d";
        gameLogger.logPlayer("MOVE_RIGHT", { key: "d" });
        break;
      case "w":
        player.velocity.y = -20;
        gameLogger.logPlayer("JUMP", { key: "w", jumpVelocity: -20 });
        break;
      case " ":
        player.attack();
        gameLogger.logPlayer("ATTACK", { key: "space" });
        break;
      // Difficulty controls for CPU
      case "1":
        enemyCPU.setDifficulty('easy');
        document.getElementById('difficulty-level').textContent = 'Easy';
        console.log("CPU difficulty set to: Easy");
        break;
      case "2":
        enemyCPU.setDifficulty('medium');
        document.getElementById('difficulty-level').textContent = 'Medium';
        console.log("CPU difficulty set to: Medium");
        break;
      case "3":
        enemyCPU.setDifficulty('hard');
        document.getElementById('difficulty-level').textContent = 'Hard';
        console.log("CPU difficulty set to: Hard");
        break;
      // Logging controls
      case "l":
        gameLogger.togglePlayerLogging();
        break;
      case "k":
        enemyCPU.toggleLogging();
        break;
      case "r":
        gameLogger.resetLogCounter();
        enemyCPU.resetLogCounter();
        break;
      case "s":
        enemyCPU.saveLogsNow();
        console.log("📁 Manual log save triggered");
        break;
    }
  }
});

window.addEventListener("keyup", (event) => {
  switch (event.key) {
    // player movement
    case "a":
      keys.a.pressed = false;
      gameLogger.logPlayer("STOP_LEFT", { key: "a released" });
      break;
    case "d":
      keys.d.pressed = false;
      gameLogger.logPlayer("STOP_RIGHT", { key: "d released" });
      break;
  }
});
