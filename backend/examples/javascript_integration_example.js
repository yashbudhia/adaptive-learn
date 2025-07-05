/**
 * JavaScript/Node.js integration example for the Adaptive Boss Behavior System
 * Can be used in web games, Electron apps, or Node.js game servers
 */

class AdaptiveBossClient {
    constructor(apiBaseUrl = 'http://localhost:8000/api/v1', gameId = null) {
        this.apiBaseUrl = apiBaseUrl;
        this.gameId = gameId;
        this.accessToken = null;
        this.actionQueue = [];
        this.isProcessingAction = false;
    }

    /**
     * Register a game with the adaptive boss system
     */
    async registerGame(gameConfig) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/games/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(gameConfig)
            });

            const result = await response.json();

            if (result.success) {
                this.gameId = result.game_id;
                this.accessToken = result.access_token;
                console.log(`✅ Game registered successfully: ${this.gameId}`);
                return result;
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            console.error('❌ Failed to register game:', error);
            throw error;
        }
    }

    /**
     * Generate a boss action based on player context
     */
    async generateBossAction(playerContext, bossHealthPercentage, battlePhase, environmentFactors = {}) {
        if (!this.accessToken) {
            throw new Error('Game not registered. Call registerGame() first.');
        }

        try {
            const requestData = {
                game_id: this.gameId,
                player_context: playerContext,
                boss_health_percentage: bossHealthPercentage,
                battle_phase: battlePhase,
                environment_factors: environmentFactors
            };

            const response = await fetch(`${this.apiBaseUrl}/boss/action`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.accessToken}`
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const bossAction = await response.json();
            console.log(`🎯 Boss action generated: ${bossAction.boss_action} (Intensity: ${bossAction.intensity})`);

            return bossAction;
        } catch (error) {
            console.error('❌ Failed to generate boss action:', error);
            throw error;
        }
    }

    /**
     * Log the outcome of a boss action for learning
     */
    async logActionOutcome(actionId, outcome, effectivenessScore, damageDealt, playerHit, executionTime, additionalMetrics = {}) {
        if (!this.accessToken) {
            throw new Error('Game not registered. Call registerGame() first.');
        }

        try {
            const outcomeData = {
                action_id: actionId,
                outcome: outcome, // 'success', 'failure', or 'partial'
                effectiveness_score: effectivenessScore,
                damage_dealt: damageDealt,
                player_hit: playerHit,
                execution_time: executionTime,
                additional_metrics: additionalMetrics
            };

            const response = await fetch(`${this.apiBaseUrl}/boss/action/outcome`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.accessToken}`
                },
                body: JSON.stringify(outcomeData)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            console.log('✅ Action outcome logged successfully');
            return result;
        } catch (error) {
            console.error('❌ Failed to log action outcome:', error);
            throw error;
        }
    }

    /**
     * Get game statistics
     */
    async getGameStats() {
        if (!this.accessToken) {
            throw new Error('Game not registered. Call registerGame() first.');
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/games/${this.gameId}/stats`, {
                headers: {
                    'Authorization': `Bearer ${this.accessToken}`
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const stats = await response.json();
            return stats;
        } catch (error) {
            console.error('❌ Failed to get game stats:', error);
            throw error;
        }
    }

    /**
     * Optimize the game's learning index
     */
    async optimizeIndex() {
        if (!this.accessToken) {
            throw new Error('Game not registered. Call registerGame() first.');
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/games/${this.gameId}/optimize`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.accessToken}`
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            console.log('✅ Index optimization started');
            return result;
        } catch (error) {
            console.error('❌ Failed to start index optimization:', error);
            throw error;
        }
    }
}

/**
 * Player behavior tracker for web games
 */
class PlayerBehaviorTracker {
    constructor() {
        this.actions = [];
        this.dodges = 0;
        this.totalActions = 0;
        this.sessionStart = Date.now();
        this.deaths = 0;
        this.reactionTimes = [];
    }

    trackAction(action) {
        this.actions.push({
            action: action,
            timestamp: Date.now()
        });
        this.totalActions++;

        // Keep only recent actions (last 50)
        if (this.actions.length > 50) {
            this.actions.shift();
        }
    }

    trackDodge() {
        this.dodges++;
        this.trackAction('dodge');
    }

    trackDeath() {
        this.deaths++;
    }

    trackReactionTime(reactionTime) {
        this.reactionTimes.push(reactionTime);

        // Keep only recent reaction times
        if (this.reactionTimes.length > 20) {
            this.reactionTimes.shift();
        }
    }

    getCurrentContext(playerHealth, equipmentLevel, difficultyPreference = 'normal') {
        const frequentActions = this.getFrequentActions();
        const dodgeFrequency = this.totalActions > 0 ? this.dodges / this.totalActions : 0;
        const avgReactionTime = this.reactionTimes.length > 0
            ? this.reactionTimes.reduce((a, b) => a + b, 0) / this.reactionTimes.length
            : 0.5;
        const sessionDuration = (Date.now() - this.sessionStart) / (1000 * 60); // minutes

        return {
            frequent_actions: frequentActions,
            dodge_frequency: Math.min(dodgeFrequency, 1.0),
            attack_patterns: this.getAttackPatterns(),
            movement_style: this.getMovementStyle(),
            reaction_time: avgReactionTime,
            health_percentage: playerHealth,
            difficulty_preference: difficultyPreference,
            session_duration: sessionDuration,
            recent_deaths: this.deaths,
            equipment_level: equipmentLevel,
            additional_context: {
                total_actions: this.totalActions,
                actions_per_minute: this.totalActions / Math.max(sessionDuration, 1)
            }
        };
    }

    getFrequentActions() {
        const actionCounts = {};
        this.actions.forEach(actionData => {
            actionCounts[actionData.action] = (actionCounts[actionData.action] || 0) + 1;
        });

        return Object.entries(actionCounts)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 5)
            .map(([action]) => action);
    }

    getAttackPatterns() {
        // Analyze sequences of actions to identify patterns
        const patterns = [];
        for (let i = 0; i < this.actions.length - 2; i++) {
            const sequence = this.actions.slice(i, i + 3).map(a => a.action).join('-');
            if (sequence.includes('attack')) {
                patterns.push(sequence);
            }
        }

        // Return most common patterns
        const patternCounts = {};
        patterns.forEach(pattern => {
            patternCounts[pattern] = (patternCounts[pattern] || 0) + 1;
        });

        return Object.entries(patternCounts)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 3)
            .map(([pattern]) => pattern);
    }

    getMovementStyle() {
        const dodgeRatio = this.totalActions > 0 ? this.dodges / this.totalActions : 0;

        if (dodgeRatio > 0.6) return 'evasive';
        if (dodgeRatio > 0.3) return 'balanced';
        return 'aggressive';
    }
}

/**
 * Example usage for a web-based RPG game
 */
async function exampleUsage() {
    console.log('🎮 Adaptive Boss System - JavaScript Example');
    console.log('='.repeat(50));

    // Initialize the client
    const bossClient = new AdaptiveBossClient();
    const behaviorTracker = new PlayerBehaviorTracker();

    try {
        // 1. Register the game
        console.log('\n1️⃣ Registering game...');
        const gameConfig = {
            game_id: 'web_rpg_001',
            name: 'Web RPG Demo',
            description: 'Browser-based RPG with adaptive boss AI',
            vocabulary: {
                boss_actions: [
                    'sword_slash', 'fire_spell', 'ice_shard', 'lightning_bolt',
                    'defensive_barrier', 'teleport_strike', 'area_explosion'
                ],
                action_types: ['attack', 'defend', 'magic', 'special'],
                environments: ['forest', 'cave', 'castle', 'arena'],
                difficulty_levels: ['easy', 'normal', 'hard', 'nightmare']
            }
        };

        await bossClient.registerGame(gameConfig);

        // 2. Simulate some player actions
        console.log('\n2️⃣ Simulating player behavior...');
        behaviorTracker.trackAction('attack');
        behaviorTracker.trackDodge();
        behaviorTracker.trackAction('spell');
        behaviorTracker.trackReactionTime(0.4);
        behaviorTracker.trackAction('attack');

        // 3. Generate boss action
        console.log('\n3️⃣ Generating boss action...');
        const playerContext = behaviorTracker.getCurrentContext(0.7, 5, 'normal');

        const bossAction = await bossClient.generateBossAction(
            playerContext,
            0.8, // boss health
            'mid_battle',
            { environment: 'forest', lighting: 'dim' }
        );

        console.log('Boss Action Details:');
        console.log(`- Action: ${bossAction.boss_action}`);
        console.log(`- Type: ${bossAction.action_type}`);
        console.log(`- Intensity: ${bossAction.intensity}`);
        console.log(`- Reasoning: ${bossAction.reasoning || 'N/A'}`);

        // 4. Simulate action execution and log outcome
        console.log('\n4️⃣ Logging action outcome...');

        // Simulate the boss action execution
        const executionResult = simulateBossActionExecution(bossAction);

        await bossClient.logActionOutcome(
            1, // action_id (would come from your game's database)
            executionResult.success ? 'success' : 'failure',
            executionResult.effectiveness,
            executionResult.damage,
            executionResult.playerHit,
            executionResult.executionTime,
            {
                player_reaction: executionResult.playerReaction,
                environmental_bonus: executionResult.environmentalBonus
            }
        );

        // 5. Get game statistics
        console.log('\n5️⃣ Getting game statistics...');
        const stats = await bossClient.getGameStats();
        console.log('Game Statistics:');
        console.log(`- Total Actions: ${stats.total_actions}`);
        console.log(`- Success Rate: ${(stats.success_rate * 100).toFixed(1)}%`);
        console.log(`- Average Effectiveness: ${(stats.avg_effectiveness * 100).toFixed(1)}%`);

        console.log('\n✨ Example completed successfully!');

    } catch (error) {
        console.error('❌ Example failed:', error);
    }
}

/**
 * Simulate boss action execution (replace with your game logic)
 */
function simulateBossActionExecution(bossAction) {
    const startTime = Date.now();

    // Simulate action execution
    const success = Math.random() > 0.3; // 70% success rate
    const damage = success ? bossAction.intensity * 30 : 0;
    const playerHit = success && Math.random() > 0.4;

    const executionTime = (Date.now() - startTime) / 1000;

    return {
        success: success,
        effectiveness: success ? Math.min(bossAction.intensity + Math.random() * 0.3, 1.0) : 0.2,
        damage: damage,
        playerHit: playerHit,
        executionTime: executionTime,
        playerReaction: playerHit ? 'hit' : 'dodged',
        environmentalBonus: Math.random() > 0.5
    };
}

// Export for Node.js or module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        AdaptiveBossClient,
        PlayerBehaviorTracker
    };
}

// Run example if this file is executed directly
if (typeof window === 'undefined' && require.main === module) {
    exampleUsage();
}