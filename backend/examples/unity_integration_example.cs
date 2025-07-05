using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using Newtonsoft.Json;

namespace AdaptiveBoss
{
    /// <summary>
    /// Unity integration example for the Adaptive Boss Behavior System
    /// </summary>
    public class AdaptiveBossManager : MonoBehaviour
    {
        [Header("API Configuration")]
        public string apiBaseUrl = "http://localhost:8000/api/v1";
        public string gameId = "unity_game_001";
        public string accessToken = "";

        [Header("Boss Configuration")]
        public GameObject bossGameObject;
        public BossController bossController;

        [Header("Player Tracking")]
        public PlayerController playerController;
        public PlayerBehaviorTracker behaviorTracker;

        private Queue<BossActionResponse> actionQueue = new Queue<BossActionResponse>();
        private bool isProcessingAction = false;

        void Start()
        {
            // Initialize the system
            StartCoroutine(InitializeSystem());
        }

        IEnumerator InitializeSystem()
        {
            Debug.Log("Initializing Adaptive Boss System...");

            // Register the game if not already registered
            if (string.IsNullOrEmpty(accessToken))
            {
                yield return StartCoroutine(RegisterGame());
            }

            Debug.Log("Adaptive Boss System initialized!");
        }

        IEnumerator RegisterGame()
        {
            var gameData = new GameRegistrationRequest
            {
                game_id = gameId,
                name = "Unity RPG Demo",
                description = "Unity-based RPG with adaptive boss AI",
                vocabulary = new GameVocabulary
                {
                    boss_actions = new string[] {
                        "melee_attack", "ranged_attack", "area_attack", "defensive_stance",
                        "charge_attack", "magic_spell", "teleport", "summon_minions"
                    },
                    action_types = new string[] { "attack", "defend", "special", "magic" },
                    environments = new string[] { "arena", "forest", "dungeon", "castle" },
                    difficulty_levels = new string[] { "easy", "normal", "hard", "expert" }
                }
            };

            string jsonData = JsonConvert.SerializeObject(gameData);
            
            using (UnityWebRequest request = UnityWebRequest.Post($"{apiBaseUrl}/games/register", jsonData, "application/json"))
            {
                yield return request.SendWebRequest();

                if (request.result == UnityWebRequest.Result.Success)
                {
                    var response = JsonConvert.DeserializeObject<GameRegistrationResponse>(request.downloadHandler.text);
                    if (response.success)
                    {
                        accessToken = response.access_token;
                        Debug.Log($"Game registered successfully! Token: {accessToken.Substring(0, 10)}...");
                    }
                    else
                    {
                        Debug.LogError($"Failed to register game: {response.message}");
                    }
                }
                else
                {
                    Debug.LogError($"Registration request failed: {request.error}");
                }
            }
        }

        public void RequestBossAction()
        {
            if (isProcessingAction) return;

            StartCoroutine(GenerateBossAction());
        }

        IEnumerator GenerateBossAction()
        {
            isProcessingAction = true;

            // Gather player context
            var playerContext = behaviorTracker.GetCurrentContext();
            
            var request = new BossActionRequest
            {
                game_id = gameId,
                player_context = playerContext,
                boss_health_percentage = bossController.GetHealthPercentage(),
                battle_phase = GetCurrentBattlePhase(),
                environment_factors = new Dictionary<string, object>
                {
                    { "environment", GetCurrentEnvironment() },
                    { "player_distance", Vector3.Distance(playerController.transform.position, bossGameObject.transform.position) }
                }
            };

            string jsonData = JsonConvert.SerializeObject(request);

            using (UnityWebRequest webRequest = UnityWebRequest.Post($"{apiBaseUrl}/boss/action", jsonData, "application/json"))
            {
                webRequest.SetRequestHeader("Authorization", $"Bearer {accessToken}");
                
                yield return webRequest.SendWebRequest();

                if (webRequest.result == UnityWebRequest.Result.Success)
                {
                    var response = JsonConvert.DeserializeObject<BossActionResponse>(webRequest.downloadHandler.text);
                    actionQueue.Enqueue(response);
                    
                    Debug.Log($"Boss action received: {response.boss_action} (Intensity: {response.intensity})");
                }
                else
                {
                    Debug.LogError($"Boss action request failed: {webRequest.error}");
                }
            }

            isProcessingAction = false;
        }

        void Update()
        {
            // Process queued boss actions
            if (actionQueue.Count > 0 && !bossController.IsExecutingAction())
            {
                var action = actionQueue.Dequeue();
                ExecuteBossAction(action);
            }
        }

        void ExecuteBossAction(BossActionResponse action)
        {
            Debug.Log($"Executing boss action: {action.boss_action}");

            // Convert API response to boss action
            var bossAction = new BossAction
            {
                actionName = action.boss_action,
                actionType = action.action_type,
                intensity = action.intensity,
                targetArea = action.target_area,
                duration = action.duration ?? 1.0f,
                animationId = action.animation_id,
                damageMultiplier = action.damage_multiplier ?? 1.0f
            };

            // Execute the action
            bossController.ExecuteAction(bossAction, (outcome) => {
                // Log the outcome back to the system
                StartCoroutine(LogActionOutcome(action, outcome));
            });
        }

        IEnumerator LogActionOutcome(BossActionResponse originalAction, ActionOutcome outcome)
        {
            var outcomeData = new ActionOutcomeData
            {
                action_id = outcome.actionId, // You'd need to store this from the database
                outcome = outcome.success ? "success" : "failure",
                effectiveness_score = outcome.effectivenessScore,
                damage_dealt = outcome.damageDealt,
                player_hit = outcome.playerHit,
                execution_time = outcome.executionTime,
                additional_metrics = new Dictionary<string, object>
                {
                    { "player_reaction", outcome.playerReaction },
                    { "environmental_bonus", outcome.environmentalBonus }
                }
            };

            string jsonData = JsonConvert.SerializeObject(outcomeData);

            using (UnityWebRequest request = UnityWebRequest.Post($"{apiBaseUrl}/boss/action/outcome", jsonData, "application/json"))
            {
                request.SetRequestHeader("Authorization", $"Bearer {accessToken}");
                
                yield return request.SendWebRequest();

                if (request.result == UnityWebRequest.Result.Success)
                {
                    Debug.Log("Action outcome logged successfully");
                }
                else
                {
                    Debug.LogError($"Failed to log action outcome: {request.error}");
                }
            }
        }

        string GetCurrentBattlePhase()
        {
            float bossHealth = bossController.GetHealthPercentage();
            
            if (bossHealth > 0.8f) return "opening";
            if (bossHealth > 0.5f) return "mid_battle";
            if (bossHealth > 0.2f) return "late_battle";
            return "final_phase";
        }

        string GetCurrentEnvironment()
        {
            // Determine environment based on scene or area
            return "arena"; // Simplified for example
        }
    }

    // Data classes for API communication
    [Serializable]
    public class GameRegistrationRequest
    {
        public string game_id;
        public string name;
        public string description;
        public GameVocabulary vocabulary;
    }

    [Serializable]
    public class GameVocabulary
    {
        public string[] boss_actions;
        public string[] action_types;
        public string[] environments;
        public string[] difficulty_levels;
    }

    [Serializable]
    public class GameRegistrationResponse
    {
        public bool success;
        public string message;
        public string game_id;
        public string access_token;
    }

    [Serializable]
    public class BossActionRequest
    {
        public string game_id;
        public PlayerContextData player_context;
        public float boss_health_percentage;
        public string battle_phase;
        public Dictionary<string, object> environment_factors;
    }

    [Serializable]
    public class PlayerContextData
    {
        public string[] frequent_actions;
        public float dodge_frequency;
        public string[] attack_patterns;
        public string movement_style;
        public float reaction_time;
        public float health_percentage;
        public string difficulty_preference;
        public float session_duration;
        public int recent_deaths;
        public int equipment_level;
        public Dictionary<string, object> additional_context;
    }

    [Serializable]
    public class BossActionResponse
    {
        public string boss_action;
        public string action_type;
        public float intensity;
        public string target_area;
        public float? duration;
        public float? cooldown;
        public string animation_id;
        public string[] sound_effects;
        public string[] visual_effects;
        public float? damage_multiplier;
        public float? success_probability;
        public string reasoning;
    }

    [Serializable]
    public class ActionOutcomeData
    {
        public int action_id;
        public string outcome;
        public float effectiveness_score;
        public float damage_dealt;
        public bool player_hit;
        public float execution_time;
        public Dictionary<string, object> additional_metrics;
    }

    // Unity-specific classes
    public class BossAction
    {
        public string actionName;
        public string actionType;
        public float intensity;
        public string targetArea;
        public float duration;
        public string animationId;
        public float damageMultiplier;
    }

    public class ActionOutcome
    {
        public int actionId;
        public bool success;
        public float effectivenessScore;
        public float damageDealt;
        public bool playerHit;
        public float executionTime;
        public string playerReaction;
        public bool environmentalBonus;
    }
}