using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using NativeWebSocket;
using Newtonsoft.Json;

namespace AdaptiveBoss.Realtime
{
    /// <summary>
    /// Unity WebSocket integration for real-time adaptive boss behavior
    /// Requires NativeWebSocket package: https://github.com/endel/NativeWebSocket-Sharp
    /// </summary>
    public class RealtimeAdaptiveBossManager : MonoBehaviour
    {
        [Header("WebSocket Configuration")]
        public string serverUrl = "ws://localhost:8000/api/v1";
        public string gameId = "unity_realtime_001";
        public string accessToken = "";

        [Header("Boss Configuration")]
        public GameObject bossGameObject;
        public BossController bossController;

        [Header("Player Tracking")]
        public PlayerController playerController;
        public PlayerBehaviorTracker behaviorTracker;

        [Header("Real-time Settings")]
        public float heartbeatInterval = 30f;
        public bool autoReconnect = true;
        public int maxReconnectAttempts = 5;

        private WebSocket websocket;
        private string sessionId;
        private bool isConnected = false;
        private int reconnectAttempts = 0;
        private Dictionary<string, BossActionRequest> pendingRequests = new Dictionary<string, BossActionRequest>();

        // Events
        public event Action OnConnected;
        public event Action OnDisconnected;
        public event Action<BossActionResponse> OnBossActionReceived;
        public event Action<LearningUpdate> OnLearningUpdate;

        void Start()
        {
            sessionId = $"unity_{SystemInfo.deviceUniqueIdentifier}_{DateTimeOffset.UtcNow.ToUnixTimeSeconds()}";
            StartCoroutine(InitializeWebSocket());
        }

        void Update()
        {
            // Dispatch WebSocket messages on main thread
            if (websocket != null)
            {
                websocket.DispatchMessageQueue();
            }
        }

        IEnumerator InitializeWebSocket()
        {
            if (string.IsNullOrEmpty(accessToken))
            {
                Debug.LogError("Access token is required for WebSocket connection");
                yield break;
            }

            yield return StartCoroutine(ConnectWebSocket());
        }

        IEnumerator ConnectWebSocket()
        {
            string wsUrl = $"{serverUrl}/ws/{gameId}?token={accessToken}&session_id={sessionId}";

            Debug.Log($"Connecting to WebSocket: {wsUrl}");

            websocket = new WebSocket(wsUrl);

            websocket.OnOpen += OnWebSocketOpen;
            websocket.OnError += OnWebSocketError;
            websocket.OnClose += OnWebSocketClose;
            websocket.OnMessage += OnWebSocketMessage;

            yield return websocket.Connect();
        }

        void OnWebSocketOpen()
        {
            Debug.Log("✅ WebSocket connected successfully");
            isConnected = true;
            reconnectAttempts = 0;

            OnConnected?.Invoke();

            // Start heartbeat
            StartCoroutine(HeartbeatCoroutine());
        }

        void OnWebSocketError(string error)
        {
            Debug.LogError($"❌ WebSocket error: {error}");
            isConnected = false;

            if (autoReconnect && reconnectAttempts < maxReconnectAttempts)
            {
                StartCoroutine(ReconnectWithDelay());
            }
        }

        void OnWebSocketClose(WebSocketCloseCode closeCode)
        {
            Debug.Log($"🔌 WebSocket closed: {closeCode}");
            isConnected = false;

            OnDisconnected?.Invoke();

            if (autoReconnect && closeCode != WebSocketCloseCode.Normal && reconnectAttempts < maxReconnectAttempts)
            {
                StartCoroutine(ReconnectWithDelay());
            }
        }

        void OnWebSocketMessage(byte[] data)
        {
            try
            {
                string json = System.Text.Encoding.UTF8.GetString(data);
                var message = JsonConvert.DeserializeObject<WebSocketMessage>(json);

                Debug.Log($"📥 Received {message.type} message");

                HandleWebSocketMessage(message);
            }
            catch (Exception e)
            {
                Debug.LogError($"Error parsing WebSocket message: {e.Message}");
            }
        }

        void HandleWebSocketMessage(WebSocketMessage message)
        {
            switch (message.type)
            {
                case "connect":
                    HandleConnectMessage(message.data);
                    break;

                case "boss_action_response":
                    HandleBossActionResponse(message.data);
                    break;

                case "learning_update":
                    HandleLearningUpdate(message.data);
                    break;

                case "heartbeat":
                    HandleHeartbeat(message.data);
                    break;

                case "error":
                    HandleError(message.data);
                    break;

                case "status":
                    HandleStatus(message.data);
                    break;

                default:
                    Debug.LogWarning($"Unknown message type: {message.type}");
                    break;
            }
        }

        void HandleConnectMessage(Dictionary<string, object> data)
        {
            Debug.Log($"🎉 Connection confirmed: {data.GetValueOrDefault("status", "unknown")}");

            if (data.ContainsKey("features"))
            {
                var features = data["features"] as List<object>;
                Debug.Log($"Available features: {string.Join(", ", features)}");
            }
        }

        void HandleBossActionResponse(Dictionary<string, object> data)
        {
            try
            {
                string requestId = data.GetValueOrDefault("request_id", "").ToString();
                var bossActionData = data["boss_action"] as Dictionary<string, object>;

                var bossAction = ParseBossActionResponse(bossActionData);
                bossAction.requestId = requestId;

                Debug.Log($"🎯 Boss Action Received: {bossAction.bossAction} (Intensity: {bossAction.intensity:F2})");

                OnBossActionReceived?.Invoke(bossAction);

                // Execute the boss action
                ExecuteBossAction(bossAction);

                // Clean up pending request
                pendingRequests.Remove(requestId);
            }
            catch (Exception e)
            {
                Debug.LogError($"Error handling boss action response: {e.Message}");
            }
        }

        void HandleLearningUpdate(Dictionary<string, object> data)
        {
            try
            {
                var learningUpdate = new LearningUpdate
                {
                    contextsLearned = Convert.ToInt32(data.GetValueOrDefault("contexts_learned", 0)),
                    avgEffectiveness = Convert.ToSingle(data.GetValueOrDefault("avg_effectiveness", 0f)),
                    performanceTrend = data.GetValueOrDefault("performance_trend", "stable").ToString()
                };

                if (data.ContainsKey("recent_improvements"))
                {
                    var improvements = data["recent_improvements"] as List<object>;
                    learningUpdate.recentImprovements = improvements?.ConvertAll(x => x.ToString()).ToArray() ?? new string[0];
                }

                Debug.Log($"🧠 Learning Update: {learningUpdate.contextsLearned} contexts, {learningUpdate.avgEffectiveness:P1} effectiveness");

                OnLearningUpdate?.Invoke(learningUpdate);
            }
            catch (Exception e)
            {
                Debug.LogError($"Error handling learning update: {e.Message}");
            }
        }

        void HandleHeartbeat(Dictionary<string, object> data)
        {
            string status = data.GetValueOrDefault("status", "").ToString();
            if (status == "ping")
            {
                // Respond to server ping
                SendHeartbeat("pong");
            }
        }

        void HandleError(Dictionary<string, object> data)
        {
            string error = data.GetValueOrDefault("error", "Unknown error").ToString();
            Debug.LogError($"❌ Server Error: {error}");
        }

        void HandleStatus(Dictionary<string, object> data)
        {
            string status = data.GetValueOrDefault("status", "").ToString();
            if (status == "processing")
            {
                string requestId = data.GetValueOrDefault("request_id", "").ToString();
                float estimatedTime = Convert.ToSingle(data.GetValueOrDefault("estimated_time", 0f));
                Debug.Log($"⏳ Server processing request {requestId} (ETA: {estimatedTime:F1}s)");
            }
        }

        public void RequestBossAction()
        {
            if (!isConnected)
            {
                Debug.LogWarning("Cannot request boss action: WebSocket not connected");
                return;
            }

            var playerContext = behaviorTracker.GetCurrentContext();
            string requestId = $"unity_req_{DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()}";

            var request = new BossActionRequest
            {
                playerContext = playerContext,
                bossHealthPercentage = bossController.GetHealthPercentage(),
                battlePhase = GetCurrentBattlePhase(),
                environmentFactors = GetEnvironmentFactors(),
                requestId = requestId
            };

            pendingRequests[requestId] = request;

            var message = new WebSocketMessage
            {
                type = "boss_action_request",
                data = new Dictionary<string, object>
                {
                    ["player_context"] = playerContext.ToDictionary(),
                    ["boss_health_percentage"] = request.bossHealthPercentage,
                    ["battle_phase"] = request.battlePhase,
                    ["environment_factors"] = request.environmentFactors,
                    ["request_id"] = requestId
                },
                sessionId = sessionId,
                gameId = gameId
            };

            SendMessage(message);
            Debug.Log($"📤 Requested boss action: {requestId}");
        }

        public void LogActionOutcome(int actionId, string outcome, float effectivenessScore,
                                   float damageDealt, bool playerHit, float executionTime,
                                   Dictionary<string, object> additionalMetrics = null)
        {
            if (!isConnected)
            {
                Debug.LogWarning("Cannot log action outcome: WebSocket not connected");
                return;
            }

            var message = new WebSocketMessage
            {
                type = "action_outcome",
                data = new Dictionary<string, object>
                {
                    ["action_id"] = actionId,
                    ["outcome"] = outcome,
                    ["effectiveness_score"] = effectivenessScore,
                    ["damage_dealt"] = damageDealt,
                    ["player_hit"] = playerHit,
                    ["execution_time"] = executionTime,
                    ["additional_metrics"] = additionalMetrics ?? new Dictionary<string, object>()
                },
                sessionId = sessionId,
                gameId = gameId
            };

            SendMessage(message);
            Debug.Log($"📊 Logged action outcome: {outcome} (effectiveness: {effectivenessScore:P1})");
        }

        void SendHeartbeat(string status = "ping")
        {
            if (!isConnected) return;

            var message = new WebSocketMessage
            {
                type = "heartbeat",
                data = new Dictionary<string, object> { ["status"] = status },
                sessionId = sessionId,
                gameId = gameId
            };

            SendMessage(message);
        }

        void SendMessage(WebSocketMessage message)
        {
            if (websocket == null || !isConnected) return;

            try
            {
                string json = JsonConvert.SerializeObject(message);
                websocket.SendText(json);
            }
            catch (Exception e)
            {
                Debug.LogError($"Error sending WebSocket message: {e.Message}");
            }
        }

        void ExecuteBossAction(BossActionResponse bossAction)
        {
            Debug.Log($"🎮 Executing boss action: {bossAction.bossAction}");

            var unityBossAction = new BossAction
            {
                actionName = bossAction.bossAction,
                actionType = bossAction.actionType,
                intensity = bossAction.intensity,
                targetArea = bossAction.targetArea,
                duration = bossAction.duration ?? 1.0f,
                animationId = bossAction.animationId,
                damageMultiplier = bossAction.damageMultiplier ?? 1.0f
            };

            bossController.ExecuteAction(unityBossAction, (outcome) =>
            {
                // Log the outcome back to the system
                LogActionOutcome(
                    actionId: 1, // You'd get this from your game database
                    outcome: outcome.success ? "success" : "failure",
                    effectivenessScore: outcome.effectivenessScore,
                    damageDealt: outcome.damageDealt,
                    playerHit: outcome.playerHit,
                    executionTime: outcome.executionTime,
                    additionalMetrics: new Dictionary<string, object>
                    {
                        ["request_id"] = bossAction.requestId,
                        ["player_reaction"] = outcome.playerReaction,
                        ["environmental_bonus"] = outcome.environmentalBonus
                    }
                );
            });
        }

        BossActionResponse ParseBossActionResponse(Dictionary<string, object> data)
        {
            return new BossActionResponse
            {
                bossAction = data.GetValueOrDefault("boss_action", "basic_attack").ToString(),
                actionType = data.GetValueOrDefault("action_type", "attack").ToString(),
                intensity = Convert.ToSingle(data.GetValueOrDefault("intensity", 0.5f)),
                targetArea = data.GetValueOrDefault("target_area", null)?.ToString(),
                duration = data.ContainsKey("duration") ? (float?)Convert.ToSingle(data["duration"]) : null,
                cooldown = data.ContainsKey("cooldown") ? (float?)Convert.ToSingle(data["cooldown"]) : null,
                animationId = data.GetValueOrDefault("animation_id", null)?.ToString(),
                damageMultiplier = data.ContainsKey("damage_multiplier") ? (float?)Convert.ToSingle(data["damage_multiplier"]) : 1.0f,
                successProbability = data.ContainsKey("success_probability") ? (float?)Convert.ToSingle(data["success_probability"]) : null,
                reasoning = data.GetValueOrDefault("reasoning", null)?.ToString(),
                responseTime = data.ContainsKey("response_time") ? (float?)Convert.ToSingle(data["response_time"]) : null
            };
        }

        string GetCurrentBattlePhase()
        {
            float bossHealth = bossController.GetHealthPercentage();

            if (bossHealth > 0.8f) return "opening";
            if (bossHealth > 0.5f) return "mid_battle";
            if (bossHealth > 0.2f) return "late_battle";
            return "final_phase";
        }

        Dictionary<string, object> GetEnvironmentFactors()
        {
            return new Dictionary<string, object>
            {
                ["environment"] = "arena", // Determine based on scene
                ["player_distance"] = Vector3.Distance(playerController.transform.position, bossGameObject.transform.position),
                ["lighting"] = "normal", // Determine based on lighting conditions
                ["obstacles"] = new string[] { "pillars", "walls" } // Determine based on environment
            };
        }

        IEnumerator HeartbeatCoroutine()
        {
            while (isConnected)
            {
                yield return new WaitForSeconds(heartbeatInterval);
                SendHeartbeat();
            }
        }

        IEnumerator ReconnectWithDelay()
        {
            reconnectAttempts++;
            float delay = Mathf.Pow(2, reconnectAttempts); // Exponential backoff

            Debug.Log($"🔄 Reconnecting in {delay} seconds (attempt {reconnectAttempts}/{maxReconnectAttempts})");
            yield return new WaitForSeconds(delay);

            yield return StartCoroutine(ConnectWebSocket());
        }

        void OnDestroy()
        {
            if (websocket != null)
            {
                websocket.Close();
            }
        }

        void OnApplicationPause(bool pauseStatus)
        {
            if (pauseStatus && websocket != null)
            {
                websocket.Close();
            }
            else if (!pauseStatus && !isConnected)
            {
                StartCoroutine(ConnectWebSocket());
            }
        }
    }

    // Data classes for WebSocket communication
    [Serializable]
    public class WebSocketMessage
    {
        public string type;
        public Dictionary<string, object> data;
        public string sessionId;
        public string gameId;
        public long timestamp;
    }

    [Serializable]
    public class BossActionRequest
    {
        public PlayerContextData playerContext;
        public float bossHealthPercentage;
        public string battlePhase;
        public Dictionary<string, object> environmentFactors;
        public string requestId;
    }

    [Serializable]
    public class BossActionResponse
    {
        public string bossAction;
        public string actionType;
        public float intensity;
        public string targetArea;
        public float? duration;
        public float? cooldown;
        public string animationId;
        public float? damageMultiplier;
        public float? successProbability;
        public string reasoning;
        public float? responseTime;
        public string requestId;
    }

    [Serializable]
    public class LearningUpdate
    {
        public int contextsLearned;
        public float avgEffectiveness;
        public string performanceTrend;
        public string[] recentImprovements;
    }
}

// Extension method for Dictionary
public static class DictionaryExtensions
{
    public static T GetValueOrDefault<T>(this Dictionary<string, object> dict, string key, T defaultValue = default(T))
    {
        if (dict.TryGetValue(key, out object value))
        {
            try
            {
                return (T)Convert.ChangeType(value, typeof(T));
            }
            catch
            {
                return defaultValue;
            }
        }
        return defaultValue;
    }
}